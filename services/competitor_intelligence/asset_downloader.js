/**
 * M.A.R.K.E.T Enterprise Platform - v4.0.5
 * Module: Competitor Asset & Image Downloader
 * Description: Downloads scraped competitor photos and assets locally to avoid hotlinking.
 */

const fs = require('fs');
const path = require('path');
const axios = require('axios');

/**
 * Ensures a directory exists synchronously.
 * @param {string} dirPath 
 */
function ensureDirectoryExists(dirPath) {
    if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true });
    }
}

/**
 * Downloads a single image from a remote URL to a local destination file.
 * @param {string} url - Remote image URL
 * @param {string} destPath - Destination file path
 * @returns {Promise<boolean>}
 */
async function downloadImage(url, destPath) {
    try {
        const response = await axios({
            method: 'GET',
            url: url,
            responseType: 'stream',
            timeout: 15000,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }
        });

        return new Promise((resolve, reject) => {
            const writer = fs.createWriteStream(destPath);
            response.data.pipe(writer);
            writer.on('finish', () => resolve(true));
            writer.on('error', (err) => {
                writer.close();
                reject(err);
            });
        });
    } catch (err) {
        console.error(`[Asset Downloader] Failed to download ${url}: ${err.message}`);
        return false;
    }
}

/**
 * Downloads multiple image URLs for a specific competitor into their isolated folder.
 * @param {number|string} competitorId - Unique competitor ID
 * @param {Array<string>} photoUrls - Array of remote image URLs
 * @param {string} baseDir - Base storage directory
 * @returns {Promise<Array<string>>} - Array of relative local image paths
 */
async function downloadCompetitorPhotos(competitorId, photoUrls, baseDir = path.join(__dirname, 'assets', 'competitors')) {
    const competitorDir = path.join(baseDir, String(competitorId));
    ensureDirectoryExists(competitorDir);

    const localPaths = [];
    const maxPhotos = Math.min(photoUrls.length, 12);

    for (let i = 0; i < maxPhotos; i++) {
        const url = photoUrls[i];
        if (!url || !url.startsWith('http')) continue;

        const filename = `photo_${Date.now()}_${i + 1}.jpg`;
        const destPath = path.join(competitorDir, filename);

        const success = await downloadImage(url, destPath);
        if (success) {
            // Return relative asset path
            const relPath = `/assets/competitors/${competitorId}/${filename}`;
            localPaths.push(relPath);
        }
    }

    return localPaths;
}

module.exports = {
    downloadImage,
    downloadCompetitorPhotos,
    ensureDirectoryExists
};
