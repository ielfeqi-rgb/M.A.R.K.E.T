"""
M.A.R.K.E.T Enterprise Platform - v4.0.5
Module: Strategic Competitive Intelligence & Opportunity Synthesis Engine
Description: Aggregates competitor data + our product catalog, enforces anti-hallucination
             grounding, and synthesizes actionable marketing and profit maximization strategies.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from database import db
from ai_provider import complete_chat, AIProviderManager
from content_filter import build_anti_hallucination_grounding_context, fetch_and_clean_url
from bot_logic import load_config

logger = logging.getLogger(__name__)


async def generate_competitive_strategy(
    competitor_ids: Optional[List[int]] = None,
    custom_instruction: str = "",
    external_url: Optional[str] = ""
) -> Dict[str, Any]:
    """
    Synthesizes a full competitive gap analysis and profit maximization plan.
    """
    try:
        # 1. Fetch competitors
        all_comps = db.list_competitors(active_only=True)
        if competitor_ids:
            target_comps = [c for c in all_comps if c["id"] in competitor_ids]
        else:
            target_comps = all_comps

        # Populate reviews for each target competitor
        populated_comps = []
        for c in target_comps:
            full_comp = db.get_competitor(c["id"])
            if full_comp:
                populated_comps.append(full_comp)

        # 2. Fetch our store products
        products = db.get_all_products()[:50]

        # 3. Handle optional external URL
        external_context = ""
        if external_url and external_url.strip():
            url_res = fetch_and_clean_url(external_url.strip())
            if url_res.get("success"):
                external_context = f"\n\n## 3. محتوى الرابط الخارجي المدخل ({url_res.get('domain')}):\n{url_res.get('clean_text')}\n"

        # 4. Build Strict Grounding Context
        grounding_data = build_anti_hallucination_grounding_context(populated_comps, products)
        if external_context:
            grounding_data += external_context

        # 5. Build Unified Strategic Synthesis Prompt
        system_instruction = "أنت المستشار الاستراتيجي وخبير نمو المبيعات (Chief Strategy & Marketing Officer) لمنظومة التجارة M.A.R.K.E.T. مهمتك هي تحليل بيانات السوق والمنافسين المرفقة ومطابقتها مع منتجاتنا وعروضنا الحالية، لاستخراج خطة استراتيجية دقيقة وموثقة لاقتناص ثغرات المنافسين وتعظيم الأرباح باللغة العربية الرسمية وبدون أي رموز تعبيرية."

        user_prompt = f"""بيانات السوق والمنافسين:
{grounding_data}

تعليمات إضافية من الإدارة:
{custom_instruction if custom_instruction else "تحليل شامل لثغرات المنافسين، مقترحات الحملات الإعلانية المضادة، وتعديلات التسعير لزيادة هوامش الربح."}

قواعد الإجابة الصارمة لمنع الهلوسة:
1. اعتمد حصرياً على البيانات المذكورة في النص ولا تخترع أسماء منافسين أو منتجات غير موجودة.
2. اذكر الأدلة من تعليقات العملاء الفعلية عند الإشارة لأي نقطة ضعف لدى المنافس.
3. قدم التقرير باللغة العربية الرسمية الفصيحة وبدون أي رموز تعبيرية (Emojis).

المطلوب صياغة التقرير بالأقسام التالية:
# تقرير التحليل الاستراتيجي واقتناص الفرص التنافسية (v4.0.5)

## 1. مصفوفة ثغرات المنافسين (Competitor Vulnerability Matrix)
- استعراض نقاط الضعف والمشاكل المتكررة التي يشتكي منها عملاؤهم مع ذكر الأدلة.

## 2. استراتيجية الهجوم التسويقي المضاد (Counter-Marketing Tactics)
- صياغة 3 أفكار إعلانية ورسائل تسويقية تضرب نقاط ضعف المنافس وتبرز تفوق منتجاتنا وخدماتنا.

## 3. خطة التسعير وهوامش الربح (Pricing & Margin Optimization)
- اقتراحات محددة لتسعير منتجاتنا أو تقديم حزم (Bundles) تزيد القيمة المدركة وهامش الربح.

## 4. فرص المخزون والمنتجات البديلة (Inventory Gap Opportunities)
- تحديد المنتجات والبدائل التي يبحث عنها العملاء وغير متوفرة أو رديئة لدى المنافس للتركيز على توفيرها.

## 5. خطة العمل التنفيذية الفورية (Action Items)
- خطوات محددة لفريق التسويق وفريق المبيعات للبدء الفوري.
"""

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ]

        # 6. Execute AI Model
        config = load_config()
        current_provider = config.get("ai_provider", "local")
        logger.info(f"[Strategic Intelligence] Dispatching prompt to AI Provider: {current_provider}")

        strategy_markdown = await complete_chat(messages, config, temperature=0.2)
        model_used = current_provider

        # 7. Save to Database
        title = f"تقرير التحليل التنافسي - {len(populated_comps)} منافسين"
        target_ids = [c["id"] for c in populated_comps]
        save_res = db.save_strategic_analysis(
            title=title,
            target_competitors=target_ids,
            strategy_markdown=strategy_markdown,
            raw_prompt=user_prompt,
            model_used=model_used
        )

        return {
            "success": True,
            "strategy_id": save_res.get("strategy_id"),
            "title": title,
            "strategy_markdown": strategy_markdown,
            "model_used": model_used,
            "competitors_analyzed": len(populated_comps),
            "products_referenced": len(products)
        }

    except Exception as e:
        logger.error(f"[Strategic Intelligence Error] {str(e)}")
        return {"success": False, "error": str(e)}

