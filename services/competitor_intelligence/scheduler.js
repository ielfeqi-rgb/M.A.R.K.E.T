/**
 * M.A.R.K.E.T Enterprise Platform - v4.0.5
 * Module: Competitor Periodic Scraping Scheduler
 * Description: Background cron daemon for monthly / bi-monthly competitor intelligence updates.
 */

const cron = require('node-cron');
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const { scrapeCompetitorData } = require('./scraper');

const CONFIG_PATH = path.join(__dirname, 'config.json');

function loadConfig() {
    try {
        if (fs.existsSync(CONFIG_PATH)) {
            return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
        }
    } catch (e) {}
    return {
        cron_expression: '0 0 1 * *', // 1st of every month at midnight
        backend_api_url: 'http://localhost:8000/api/competitors/save-snapshot',
        competitors: []
    };
}

async function runScheduledScraping() {
    console.log(`[Scheduler] Triggered scheduled competitor scraping at ${new Date().toISOString()}`);
    const config = loadConfig();

    for (const comp of config.competitors || []) {
        if (!comp.url) continue;
        console.log(`[Scheduler] Processing competitor #${comp.id} (${comp.name || comp.url})...`);
        try {
            const data = await scrapeCompetitorData(comp.url, comp.id);
            // Post result to FastAPI backend
            await axios.post(config.backend_api_url, data, { timeout: 10000 }).catch(e => {
                console.warn(`[Scheduler] Backend sync notice: ${e.message}`);
            });
        } catch (err) {
            console.error(`[Scheduler] Failed competitor #${comp.id}: ${err.message}`);
        }
    }
    console.log(`[Scheduler] Scheduled scraping cycle completed.`);
}

// Default schedule: First day of every month at 00:00
const initialConfig = loadConfig();
const cronExpr = initialConfig.cron_expression || '0 0 1 * *';

console.log(`[Competitor Scheduler] Initialized with schedule: "${cronExpr}"`);
cron.schedule(cronExpr, () => {
    runScheduledScraping();
});

if (require.main === module) {
    console.log('[Competitor Scheduler Daemon] Running in standalone background mode...');
}

module.exports = {
    runScheduledScraping,
    loadConfig
};
