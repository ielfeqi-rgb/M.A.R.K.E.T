-- Meta Facebook Messenger Adapter (Lua)
-- Author: M.A.R.K.E.T. AI Systems

function process(input)
    local raw_msg = input.user_message or ""
    local sender_psid = (input.metadata and (input.metadata.sender_id or input.metadata.psid)) or "fb_psid_999"
    local customer_name = (input.metadata and input.metadata.customer_name) or "عميل فيسبوك"
    local platform = "facebook_messenger"

    local system_prompt = [[
أنت ممثل خدمة العملاء الرسمي لصفحة فيسبوك. 
تحدث بأسلوب ترحيبي محترف وواضح باللغة العربية.
اجعل الإجابة شائقة واعرض المساعدة في أسرع وقت.
]]

    return {
        status = "success",
        plugin = "facebook_messenger",
        platform = platform,
        sender_id = sender_psid,
        injected_context = string.format([[
[محول Facebook Messenger Adapter - Lua]:
- القناة: محادثة صفحة فيسبوك الرسمية (Messenger Webhook)
- المعرف الفريد (PSID): %s
- اسم العميل: %s
- النمط المطلوب: رد ترحيبي مهني وسريع
]], sender_psid, customer_name),
        system_instruction_override = system_prompt,
        outbound_meta = {
            recipient = { id = sender_psid },
            messaging_type = "RESPONSE",
            platform = "facebook",
            endpoint = "https://graph.facebook.com/v19.0/me/messages"
        }
    }
end
