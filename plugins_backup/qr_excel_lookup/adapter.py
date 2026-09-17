# QR / Barcode & Inventory Excel Lookup Adapter (Python)
# Author: M.A.R.K.E.T. AI Systems
import re

def process(input_data):
    msg = input_data.get("user_message", "")
    
    # Mock database
    inventory = {
        "6291038475012": {"item": "شاحن سريع Type-C 65W", "rack": "A-12", "qty": 45, "status": "متاح"},
        "6291038475099": {"item": "سماعة بلوتوث Pro Max", "rack": "B-04", "qty": 3, "status": "مخزون حرج"},
        "QR-9904": {"item": "شاشة حماية ايفون 15 Pro", "rack": "C-01", "qty": 120, "status": "متاح"}
    }
    
    found_code = None
    for code in inventory:
        if code.lower() in msg.lower():
            found_code = code
            break
            
    if found_code:
        item = inventory[found_code]
        return {
            "status": "success",
            "plugin": "qr_excel_lookup",
            "injected_context": f"[نتائج البحث بالباركود {found_code}]:\n- الصنف: {item['item']}\n- الرف/المكان: {item['rack']}\n- الكمية بالمخزن: {item['qty']} قطعة\n- الحالة: {item['status']}",
            "system_instruction_override": "أنت موظف إدارة المخازن والجرد. أبلغ المستخدم بموقع الصنف والكمية المتاحة بدقة."
        }
        
    return {
        "status": "neutral",
        "plugin": "qr_excel_lookup",
        "injected_context": "[الجرد]: لم يتم مسح رمز باركود أو QR صحيح في الرسالة.",
        "system_instruction_override": "اطلب من المستخدم قراءة الباركود أو إدخال الرقم التسلسلي للصنف."
    }
