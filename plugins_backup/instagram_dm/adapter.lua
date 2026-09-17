-- Instagram Direct Messaging Webhook Adapter (Lua)
-- Author: M.A.R.K.E.T. AI Systems

function process(input)
    local raw_msg = input.user_message or ""
    local ig_user_id = (input.metadata and (input.metadata.sender_id or input.metadata.ig_id)) or "ig_user_404"
    local customer_name = (input.metadata and input.metadata.customer_name) or "متابع إنستجرام"
    local platform = "instagram"
    local db_context = input.db_context or ""

    local system_prompt = string.format([[
أنت ممثل خدمة العملاء الرسمي لصفحة إنستجرام (Instagram Direct).
بيانات المنتجات والمخزون المؤكدة:
%s

تعليمات محادثات إنستجرام:
1. استخدم لغة عصرية وأنيقة ومختصرة تناسب محادثات إنستجرام وستوري الردود.
2. اعرض السعر المخفض والمقاسات المتاحة بدقة تامة وبدون تأليف.
3. شجع العميل على إرسال العنوان ورقم الهاتف لتجهيز الأوردر فوراً.
]], db_context)

    return {
        status = "success",
        plugin = "instagram_dm",
        platform = platform,
        sender_id = ig_user_id,
        injected_context = string.format([[
[محول Instagram Direct Adapter - Lua]:
- قناة الاستقبال: رسالة خاصة على إنستجرام (Instagram DM)
- معرف الحساب (IGSID): %s
- اسم المتابع: %s
- بروتوكول الإرسال: Meta Graph API for Instagram (/v19.0/me/messages)
]], ig_user_id, customer_name),
        system_instruction_override = system_prompt,
        outbound_meta = {
            recipient = { id = ig_user_id },
            messaging_type = "RESPONSE",
            platform = "instagram",
            endpoint = "https://graph.facebook.com/v19.0/me/messages"
        }
    }
end
