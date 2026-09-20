/**
 * M.A.R.K.E.T Enterprise Platform - v4.0.5
 * Module: Multi-Language Sentiment Analyzer & Keyword Extractor
 * Description: Rule-based & Lexicon classifier for Arabic & English customer reviews.
 */

// Arabic positive & negative sentiment indicator dictionaries
const ARABIC_POSITIVE_WORDS = [
    'ممتاز', 'ممتازة', 'رائع', 'رائعة', 'جميل', 'جميلة', 'سريع', 'سريعة',
    'محترم', 'محترمين', 'أفضل', 'افضل', 'جودة', 'عالية', 'مميز', 'مميزة',
    'انصح', 'أنصح', 'توصيل سريع', 'خدمة ممتازة', 'شكرا', 'شكراً', 'تجربة رائعة',
    'نظيف', 'نظافة', 'تعامل راقي', 'امانة', 'أمانة', 'سعره مناسب', 'رخيص'
];

const ARABIC_NEGATIVE_WORDS = [
    'سيء', 'سيئة', 'بطيء', 'بطيئة', 'غالي', 'غالية', 'تأخير', 'تاخير',
    'نصابين', 'سرقة', 'غير محترم', 'زبالة', 'رديء', 'رديئة', 'تالف',
    'لا انصح', 'لا أنصح', 'خدمة سيئة', 'تعامل سيء', 'ضياع', 'تجربة فاشلة',
    'مغشوش', 'نقص', 'بارد', 'غير مطابق', 'اسعار مبالغ', 'أسعار مبالغ', 'ندمان'
];

const ENGLISH_POSITIVE_WORDS = [
    'excellent', 'great', 'awesome', 'good', 'best', 'fast', 'recommend',
    'friendly', 'perfect', 'amazing', 'superb', 'quality', 'clean', 'helpful'
];

const ENGLISH_NEGATIVE_WORDS = [
    'bad', 'terrible', 'worst', 'slow', 'expensive', 'delay', 'delayed',
    'scam', 'poor', 'dirty', 'rude', 'broken', 'never again', 'waste', 'horrible'
];

/**
 * Classifies sentiment of a single review text.
 * @param {string} text - Review text
 * @param {number} rating - Star rating (1-5)
 * @returns {{sentiment: 'positive'|'negative'|'neutral', score: number, keywords: Array<string>}}
 */
function analyzeReviewSentiment(text = '', rating = 0) {
    const lowerText = text.toLowerCase();
    let score = 0;
    const foundKeywords = [];

    // Check Arabic positive
    ARABIC_POSITIVE_WORDS.forEach(word => {
        if (text.includes(word)) {
            score += 1.5;
            foundKeywords.push(word);
        }
    });

    // Check Arabic negative
    ARABIC_NEGATIVE_WORDS.forEach(word => {
        if (text.includes(word)) {
            score -= 2.0;
            foundKeywords.push(word);
        }
    });

    // Check English positive
    ENGLISH_POSITIVE_WORDS.forEach(word => {
        if (lowerText.includes(word)) {
            score += 1.5;
            foundKeywords.push(word);
        }
    });

    // Check English negative
    ENGLISH_NEGATIVE_WORDS.forEach(word => {
        if (lowerText.includes(word)) {
            score -= 2.0;
            foundKeywords.push(word);
        }
    });

    // Weight with star rating if available
    if (rating >= 4) score += 2.0;
    if (rating === 3) score += 0.0;
    if (rating <= 2 && rating > 0) score -= 2.5;

    let sentiment = 'neutral';
    if (score >= 1.0) sentiment = 'positive';
    else if (score <= -1.0) sentiment = 'negative';

    return {
        sentiment,
        score: Math.round(score * 10) / 10,
        keywords: Array.from(new Set(foundKeywords))
    };
}

/**
 * Summarizes a batch of reviews into sentiment aggregates and key pain points.
 * @param {Array<{text: string, rating: number}>} reviews 
 * @returns {Object}
 */
function summarizeReviewsBatch(reviews = []) {
    let positiveCount = 0;
    let negativeCount = 0;
    let neutralCount = 0;
    const keywordFrequency = {};

    reviews.forEach(r => {
        const res = analyzeReviewSentiment(r.text, r.rating);
        r.sentiment = res.sentiment;
        r.keywords = res.keywords;

        if (res.sentiment === 'positive') positiveCount++;
        else if (res.sentiment === 'negative') negativeCount++;
        else neutralCount++;

        res.keywords.forEach(kw => {
            keywordFrequency[kw] = (keywordFrequency[kw] || 0) + 1;
        });
    });

    const topKeywords = Object.entries(keywordFrequency)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10)
        .map(([word, count]) => ({ word, count }));

    return {
        total_analyzed: reviews.length,
        positive_count: positiveCount,
        negative_count: negativeCount,
        neutral_count: neutralCount,
        top_keywords: topKeywords
    };
}

module.exports = {
    analyzeReviewSentiment,
    summarizeReviewsBatch
};
