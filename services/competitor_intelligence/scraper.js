/**
 * M.A.R.K.E.T Enterprise Platform - v4.0.5
 * Module: Google Maps Competitor Intelligence Scraper
 * Description: Resilient Headless Scraper utilizing Puppeteer-Extra with Stealth Plugin.
 */

const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs');
const path = require('path');
const { downloadCompetitorPhotos } = require('./asset_downloader');
const { summarizeReviewsBatch } = require('./sentiment_analyzer');

puppeteer.use(StealthPlugin());

/**
 * Initializes Puppeteer browser in stealth headless mode.
 */
async function initializeBrowser() {
    const browser = await puppeteer.launch({
        headless: 'new',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--disable-gpu',
            '--window-size=1920,1080',
            '--lang=ar-EG,ar,en-US,en'
        ]
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080 });
    await page.setUserAgent(
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    );

    return { browser, page };
}

/**
 * Auto-scrolls Google Maps review container.
 */
async function autoScrollContainer(page, containerSelector, maxScrollAttempts = 15) {
    try {
        await page.waitForSelector(containerSelector, { timeout: 8000 });
        await page.evaluate(async (selector, maxAttempts) => {
            const container = document.querySelector(selector);
            if (!container) return;

            let previousHeight = 0;
            let attempts = 0;

            while (attempts < maxAttempts) {
                container.scrollTop = container.scrollHeight;
                await new Promise((resolve) => setTimeout(resolve, 1200));

                const currentHeight = container.scrollHeight;
                if (currentHeight === previousHeight) {
                    await new Promise((resolve) => setTimeout(resolve, 1500));
                    if (container.scrollHeight === previousHeight) break;
                }

                previousHeight = currentHeight;
                attempts++;
            }
        }, containerSelector, maxScrollAttempts);
    } catch (err) {
        console.warn(`[Scraper] Scroll container timeout or not found: ${err.message}`);
    }
}

/**
 * Scrapes a single competitor Google Maps profile.
 * @param {string} targetUrl - Google Maps URL
 * @param {string|number} competitorId - Target ID
 * @param {number} maxReviews - Review limit
 * @returns {Promise<Object>}
 */
async function scrapeCompetitorData(targetUrl, competitorId = 'default', maxReviews = 40) {
    const { browser, page } = await initializeBrowser();
    const result = {
        competitor_id: competitorId,
        url: targetUrl,
        competitor_name: '',
        rating: 0,
        total_reviews_count: 0,
        address: '',
        category: '',
        scraped_at: new Date().toISOString(),
        reviews: [],
        photo_urls: [],
        local_photos: [],
        sentiment_summary: {}
    };

    try {
        console.log(`[Scraper] Navigating to: ${targetUrl}`);
        await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
        await page.waitForTimeout(3000);

        // Extract Business Name
        result.competitor_name = await page.evaluate(() => {
            const h1 = document.querySelector('h1.DUwDvf') || document.querySelector('h1');
            return h1 ? h1.innerText.trim() : 'المنافس';
        });

        // Extract Core Stats
        const stats = await page.evaluate(() => {
            const ratingEl = document.querySelector('span.ceNzKf') || document.querySelector('div.F7nice span');
            const reviewsCountEl = document.querySelector('span[aria-label*="مراجعة"]') || 
                                   document.querySelector('span[aria-label*="reviews"]') || 
                                   document.querySelector('div.F7nice span:nth-child(2)');
            const addressBtn = document.querySelector('button[data-item-id="address"]');
            const categoryBtn = document.querySelector('button[jsaction*="category"]');

            const rating = ratingEl ? parseFloat(ratingEl.innerText.replace(',', '.')) : 0;
            let reviewsCount = 0;

            if (reviewsCountEl) {
                const cleanText = reviewsCountEl.innerText.replace(/[^0-9]/g, '');
                reviewsCount = cleanText ? parseInt(cleanText, 10) : 0;
            }

            return {
                rating: isNaN(rating) ? 0 : rating,
                total_reviews_count: reviewsCount,
                address: addressBtn ? addressBtn.innerText.trim() : '',
                category: categoryBtn ? categoryBtn.innerText.trim() : ''
            };
        });

        result.rating = stats.rating;
        result.total_reviews_count = stats.total_reviews_count;
        result.address = stats.address;
        result.category = stats.category;

        // Try Clicking Reviews Tab
        const reviewsTabSelector = 'button[role="tab"][aria-label*="مراجعات"], button[role="tab"][aria-label*="Reviews"]';
        const reviewsTab = await page.$(reviewsTabSelector);
        
        if (reviewsTab) {
            await reviewsTab.click();
            await page.waitForTimeout(2000);

            const scrollContainerSelector = 'div.m6QErb.DxyBCb.kA9KIf.dS8AEf';
            await autoScrollContainer(page, scrollContainerSelector, Math.ceil(maxReviews / 10));

            result.reviews = await page.evaluate((limit) => {
                const items = Array.from(document.querySelectorAll('div.jftiEf'));
                return items.slice(0, limit).map((el) => {
                    const authorEl = el.querySelector('div.d4r55');
                    const textEl = el.querySelector('span.wiI7pd');
                    const dateEl = el.querySelector('span.rsqaWe');
                    const starsEl = el.querySelector('span.kvMYJc');

                    let stars = 0;
                    if (starsEl) {
                        const label = starsEl.getAttribute('aria-label') || '';
                        const match = label.match(/([0-9]+)/);
                        if (match) stars = parseInt(match[1], 10);
                    }

                    return {
                        author: authorEl ? authorEl.innerText.trim() : 'Anonymous',
                        rating: stars,
                        text: textEl ? textEl.innerText.trim() : '',
                        date_text: dateEl ? dateEl.innerText.trim() : '',
                        extracted_at: new Date().toISOString()
                    };
                });
            }, maxReviews);
        }

        // Extract Photos
        result.photo_urls = await page.evaluate(() => {
            const imgElements = Array.from(document.querySelectorAll('button[jsaction*="photo"] img, div.m6QErb img'));
            return Array.from(new Set(
                imgElements
                    .map(img => img.src)
                    .filter(src => src && src.startsWith('http') && !src.includes('data:image'))
            )).slice(0, 10);
        });

        // Run Sentiment Analysis on Scraped Reviews
        result.sentiment_summary = summarizeReviewsBatch(result.reviews);

        // Download Photos Locally
        if (result.photo_urls.length > 0) {
            result.local_photos = await downloadCompetitorPhotos(competitorId, result.photo_urls);
        }

        console.log(`[Scraper] Scraped "${result.competitor_name}": ${result.rating} stars, ${result.total_reviews_count} reviews, ${result.reviews.length} items parsed.`);
        return result;

    } catch (error) {
        console.error(`[Scraper Error] ${error.message}`);
        result.error = error.message;
        return result;
    } finally {
        await browser.close();
    }
}

// CLI Execution support
if (require.main === module) {
    const args = process.argv.slice(2);
    const targetUrl = args[0] || 'https://maps.app.goo.gl/example';
    const targetId = args[1] || '1';

    scrapeCompetitorData(targetUrl, targetId)
        .then(data => {
            console.log(JSON.stringify(data, null, 2));
            process.exit(0);
        })
        .catch(err => {
            console.error(err);
            process.exit(1);
        });
}

module.exports = {
    initializeBrowser,
    autoScrollContainer,
    scrapeCompetitorData
};
