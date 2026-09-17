-- Real Estate Mortgage & Payment Calculator Adapter (Lua)
-- Author: M.A.R.K.E.T. AI Systems

function process(input)
    local msg = string.lower(input.user_message or "")
    
    local projects = {
        ["العاصمة"] = { name = "كمبوند الفلك - العاصمة الإدارية", price_from = 2500000, years = 8, downpayment = 10, delivery = "2026 Q4" },
        ["التجمع"] = { name = "برج النخيل - القاهرة الجديدة", price_from = 3800000, years = 7, downpayment = 15, delivery = "2025 Q2" },
        ["الشيخ زايد"] = { name = "فيلا بالما - الشيخ زايد", price_from = 6200000, years = 10, downpayment = 10, delivery = "جاهز للتسليم" }
    }
    
    for loc, p in pairs(projects) do
        if string.find(msg, loc) then
            local down_val = (p.price_from * p.downpayment) / 100
            local rem = p.price_from - down_val
            local monthly = rem / (p.years * 12)
            
            return {
                status = "success",
                plugin = "real_estate_calc",
                injected_context = string.format([[
[حاسبة التمويل العقاري - بيانات مشروع %s]:
- المشروع: %s
- السعر يبدأ من: %d ج.م
- المقدم المطلوب (%d%%): %d ج.م
- فترة التقسيط: %d سنوات
- القسط الشهري المتوقع: ~%d ج.م/شهرياً
- موعد التسليم: %s
]], loc, p.name, p.price_from, p.downpayment, down_val, p.years, math.floor(monthly), p.delivery),
                system_instruction_override = "أنت مستشار عقاري خبير ورصين. قدم الحسبة العقارية أعلاه للعميل بأسلوب وثيق واحترافي وشجعه على حجز موعد زيارة للموقع."
            }
        end
    end
    
    return {
        status = "neutral",
        plugin = "real_estate_calc",
        injected_context = "[المشروعات المتاحة]: العاصمة الإدارية، التجمع الخامس، والشيخ زايد.",
        system_instruction_override = "رحب بالمشتري واسأله عن المنطقة المفضلة لديه (العاصمة، التجمع، الشيخ زايد) لحساب الأقساط بدقة."
    }
end
