"""
M.A.R.K.E.T Enterprise Platform - v4.0.5
Module: Content Sanitizer & Anti-Hallucination Grounding Filter
Description: Converts raw web pages, social posts, and scraped reviews into clean
             Reader-Mode text, stripping noise and enforcing strict grounding directives.
"""

import re
import html
from typing import Dict, Any, List, Optional
import urllib.request
from urllib.parse import urlparse


def clean_html_to_reader_mode(raw_html: str, max_chars: int = 8000) -> str:
    """
    Transforms raw HTML into concise, readable markdown text.
    Strips scripts, styles, navigations, footers, and advertising noise.
    """
    if not raw_html:
        return ""

    # 1. Strip script, style, svg, noscript, and iframe blocks
    cleaned = re.sub(r'<(script|style|svg|noscript|iframe|header|footer|nav)[\s\S]*?</\1>', ' ', raw_html, flags=re.IGNORECASE)
    
    # 2. Strip comments
    cleaned = re.sub(r'<!--[\s\S]*?-->', ' ', cleaned)

    # 3. Replace common block elements with newlines
    cleaned = re.sub(r'<(p|div|section|article|li|tr|h1|h2|h3|h4|h5|h6)[^>]*>', '\n', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<br\s*/?>', '\n', cleaned, flags=re.IGNORECASE)

    # 4. Remove all remaining tags
    cleaned = re.sub(r'<[^>]+>', ' ', cleaned)

    # 5. Decode HTML entities
    cleaned = html.unescape(cleaned)

    # 6. Normalize whitespace and blank lines
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    text = '\n'.join(lines)

    # 7. Deduplicate repeating lines (e.g. cookie banners, duplicate buttons)
    seen = set()
    unique_lines = []
    for line in text.splitlines():
        if len(line) < 3:
            continue
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)

    filtered_text = '\n'.join(unique_lines)
    if len(filtered_text) > max_chars:
        filtered_text = filtered_text[:max_chars] + "\n...[تم اقتطاع بقية الصفحة لتفادي تجاوز سعة الذاكرة]..."

    return filtered_text


def fetch_and_clean_url(url: str, timeout: int = 15) -> Dict[str, Any]:
    """
    Fetches a remote URL and converts it into sanitized Reader Mode markdown.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return {"success": False, "error": "رابط غير صالح"}

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.7,en;q=0.3"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            raw_data = response.read()

            # Attempt decoding
            encoding = "utf-8"
            if "charset=" in content_type:
                encoding = content_type.split("charset=")[-1].strip()

            try:
                raw_html = raw_data.decode(encoding, errors="replace")
            except Exception:
                raw_html = raw_data.decode("utf-8", errors="replace")

            cleaned_text = clean_html_to_reader_mode(raw_html)

            # Extract title if possible
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', raw_html, re.IGNORECASE)
            title = html.unescape(title_match.group(1).strip()) if title_match else parsed.netloc

            return {
                "success": True,
                "url": url,
                "title": title,
                "domain": parsed.netloc,
                "clean_text": cleaned_text,
                "char_count": len(cleaned_text)
            }
    except Exception as e:
        return {"success": False, "error": f"فشل جلب محتوى الرابط: {str(e)}"}


def build_anti_hallucination_grounding_context(competitors_data: List[Dict[str, Any]], store_products: List[Dict[str, Any]]) -> str:
    """
    Assembles competitor data and our store products into a strictly grounded,
    structured markdown context with explicit anti-hallucination directives.
    """
    context_lines = []
    context_lines.append("# بيانات السوق والتحليل التنافسي الموثقة (Strict Grounding Context)")
    context_lines.append("تنبيه صارم: اعتمد حصرياً على البيانات المرفقة أدناه. يمنع منعاً باتاً افتراض أو اختلاق أي تفاصيل غير واردة في النصوص.")
    context_lines.append("")

    # 1. Competitors Section
    context_lines.append("## 1. بيانات المنافسين في النطاق الجغرافي:")
    for i, comp in enumerate(competitors_data, 1):
        name = comp.get("name", f"منافس #{i}")
        rating = comp.get("latest_rating", comp.get("rating", 0.0))
        rev_count = comp.get("latest_reviews_count", comp.get("total_reviews_count", 0))
        r_delta = comp.get("rating_delta", 0.0)
        c_delta = comp.get("reviews_delta", 0)
        category = comp.get("category", "غير محدد")
        address = comp.get("address", "غير محدد")

        delta_str = f"(مؤشر التقييم: {'+' if r_delta > 0 else ''}{r_delta}, مراجعات جديدة: {'+' if c_delta > 0 else ''}{c_delta})"

        context_lines.append(f"### [منافس {i}] {name}")
        context_lines.append(f"- الفئة: {category} | العنوان: {address}")
        context_lines.append(f"- التقييم الإجمالي: {rating} من 5 نجوم (إجمالي المراجعات: {rev_count}) {delta_str}")

        # Reviews highlights
        reviews = comp.get("reviews", [])
        if reviews:
            context_lines.append("- مقتطفات من تعليقات العملاء الفعلية:")
            for rev in reviews[:8]:
                r_text = rev.get("text", "").strip()
                r_stars = rev.get("rating", 0)
                r_author = rev.get("author", "عميل")
                if r_text:
                    context_lines.append(f"  * [{r_stars} نجوم] ({r_author}): \"{r_text}\"")
        context_lines.append("")

    # 2. Store Products Section
    context_lines.append("## 2. بيانات متجرنا وكتالوج المنتجات الحالي:")
    if store_products:
        for p in store_products[:25]:
            code = p.get("code", "")
            p_name = p.get("name", "")
            price = p.get("price", 0.0)
            stock = p.get("stock", 0)
            desc = p.get("description", "")
            context_lines.append(f"- [{code}] {p_name} | السعر: {price} ج.م | المخزون المتاح: {stock} قطعة {f'({desc})' if desc else ''}")
    else:
        context_lines.append("- (كتالوج المنتجات فارغ حالياً - التركيز على نقاط القوة العامة وسرعة الخدمة).")

    return '\n'.join(context_lines)
