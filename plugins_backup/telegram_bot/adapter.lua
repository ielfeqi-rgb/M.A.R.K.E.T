-- Telegram Bot Webhook Adapter (Lua)
-- Author: M.A.R.K.E.T. AI Systems

function process(input)
    local chat_id = (input.metadata and (input.metadata.chat_id or input.metadata.sender_id)) or "12345678"
    local username = (input.metadata and input.metadata.username) or "TelegramUser"

    return {
        status = "success",
        plugin = "telegram_bot",
        injected_context = string.format([[
[محول Telegram Bot Adapter - Lua]:
- معرف المحادثة (Chat ID): %s
- اسم المستخدم: @%s
- النمط: منسق بصيغة HTML أو Markdown لتلجرام.
]], chat_id, username),
        system_instruction_override = "أنت مساعد Telegram ذكي وسريع. قدم الإجابة منسقة بعناية واستخدم الإيموجي المناسب.",
        outbound_meta = {
            chat_id = chat_id,
            parse_mode = "HTML",
            platform = "telegram"
        }
    }
end
