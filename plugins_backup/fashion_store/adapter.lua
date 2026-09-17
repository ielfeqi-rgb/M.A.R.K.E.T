-- Fashion Store Context & Discount Injector (Lua)
-- Author: M.A.R.K.E.T. AI Systems

function process(input)
    local msg = string.lower(input.user_message or "")
    local customer = (input.metadata and input.metadata.customer_name) or "العميل"
    
    local catalog = {
        ["ts-102"] = { name = "تيشيرت أوفرسايز قطن 100% (أسود/أبيض)", price = 350, discount_price = 295, sizes = "M, L, XL", stock = 14 },
        ["hd-505"] = { name = "سويت شيرت هودي شتوي مبطن", price = 650, discount_price = 520, sizes = "L, XL, XXL", stock = 4 },
        ["pn-204"] = { name = "بنطلون جينز كارجو زيتي", price = 480, discount_price = 420, sizes = "32, 34, 36", stock = 0 }
    }
    
    local matched_code = nil
    for code, item in pairs(catalog) do
        if string.find(msg, code, 1, true) or string.find(msg, string.upper(code), 1, true) then
            matched_code = code
            break
        end
    end
    
    if matched_code then
        local item = catalog[matched_code]
        local stock_status = item.stock > 0 and ("متاح في المخزن (" .. item.stock .. " قطعة)") or "نفذت الكمية حالياً"
        
        return {
            status = "success",
            plugin = "fashion_store",
            injected_context = string.format([[
[بيانات المنتج الدقيقة من السيستم الداخلي]:
- المنتج: %s
- الكود: %s
- السعر الأصلي: %d ج.م
- السعر بالعرض الحالي: %d ج.م (توفير %d ج.م!)
- المقاسات: %s
- المخزون: %s
- العميل: %s
]], item.name, string.upper(matched_code), item.price, item.discount_price, (item.price - item.discount_price), item.sizes, stock_status, customer),
            system_instruction_override = "أنت مساعد خدمة عملاء متجر ملابس أنيق ولبق. أجب على العميل مستخدماً بيانات المنتج أعلاه فقط بدقة تامة وبدون أي تأليف."
        }
    end
    
    if string.find(msg, "شحن", 1, true) or string.find(msg, "توصيل", 1, true) then
        return {
            status = "success",
            plugin = "fashion_store",
            injected_context = "[سياسة الشحن]: التوصيل لجميع المحافظات خلال 2-4 أيام عمل بـ 45 ج.م. الشحن مجاني للطلبات فوق 600 ج.م.",
            system_instruction_override = "أخبر العميل بسياسة التوصيل بأسلوب ترحيبي مشجع."
        }
    end
    
    return {
        status = "neutral",
        plugin = "fashion_store",
        injected_context = "[المتجر]: لم يذكر العميل كود منتج محدد. اسأله بلطف عن القطعة أو الكود لمساعدته.",
        system_instruction_override = "رحب بالعميل واطلب منه تحديد القطعة أو كود المنتج مثل TS-102."
    }
end
