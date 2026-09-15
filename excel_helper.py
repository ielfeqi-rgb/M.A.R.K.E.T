import threading
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import openpyxl
from settings import settings

logger = logging.getLogger(__name__)


class ExcelCache:
    """
    Lightweight, pure Python Excel Manager using openpyxl directly.
    Zero C-compilation dependencies (does not require pandas/numpy/gcc).
    """
    def __init__(self, file_path: str, reload_interval: int = 300):
        self.file_path = Path(file_path)
        self.reload_interval = reload_interval
        self._cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._lock = threading.RLock()
        self._last_load = 0.0
        self.columns = [
            "كود المنتج",
            "اسم المنتج",
            "السعر",
            "المقاس",
            "اللون",
            "الكمية المتاحة",
            "الوصف"
        ]

    def _read_excel_data(self) -> Optional[List[Dict[str, Any]]]:
        if not self.file_path.exists():
            logger.warning(f"Excel file not found: {self.file_path}. Creating default template...")
            self.create_template()

        try:
            wb = openpyxl.load_workbook(self.file_path, data_only=True)
            sheet = wb.active
            rows = list(sheet.iter_rows(values_only=True))
            if not rows:
                return []

            headers = [str(h).strip() if h is not None else "" for h in rows[0]]
            data = []
            for row in rows[1:]:
                if not any(row):
                    continue
                row_dict = {}
                for idx, col_name in enumerate(headers):
                    if not col_name:
                        continue
                    val = row[idx] if idx < len(row) else None
                    row_dict[col_name] = "" if val is None else val
                data.append(row_dict)
            wb.close()
            return data
        except Exception as e:
            logger.error(f"Failed to read Excel file: {e}")
            return None

    def _build_index(self, data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        index = {}
        for row in data:
            code = str(row.get("كود المنتج", "")).strip().lower()
            if code:
                # Ensure all expected columns exist
                for col in self.columns:
                    row.setdefault(col, "")
                index[code] = row
        return index

    def reload(self) -> bool:
        with self._lock:
            data = self._read_excel_data()
            if data is not None:
                self._cache = self._build_index(data)
                self._last_load = time.time()
                logger.info(f"Excel reloaded: {len(self._cache)} products indexed")
                return True
            return False

    def get_product(self, code: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._cache is None or (time.time() - self._last_load > self.reload_interval):
                if not self.reload():
                    return None

            clean_code = str(code).strip().lower()
            return self._cache.get(clean_code)

    def get_all_products(self) -> List[Dict[str, Any]]:
        with self._lock:
            if self._cache is None:
                self.reload()
            return list(self._cache.values()) if self._cache else []

    def get_all_codes(self) -> List[str]:
        with self._lock:
            if self._cache is None:
                self.reload()
            return list(self._cache.keys()) if self._cache else []

    def save_products(self, products_list: List[Dict[str, Any]]) -> bool:
        with self._lock:
            try:
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Products"

                # Write headers
                headers = self.columns
                ws.append(headers)

                # Write product rows
                for p in products_list:
                    row = [p.get(col, "") for col in headers]
                    ws.append(row)

                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                wb.save(self.file_path)
                wb.close()
                self.reload()
                logger.info(f"Saved {len(products_list)} products to Excel successfully")
                return True
            except Exception as e:
                logger.error(f"Error saving products to Excel: {e}")
                return False

    def add_or_update_product(self, product_data: Dict[str, Any]) -> bool:
        with self._lock:
            current_products = self.get_all_products()
            code = str(product_data.get("كود المنتج", "")).strip().lower()
            if not code:
                return False

            updated = False
            for i, p in enumerate(current_products):
                if str(p.get("كود المنتج", "")).strip().lower() == code:
                    current_products[i] = product_data
                    updated = True
                    break

            if not updated:
                current_products.append(product_data)

            return self.save_products(current_products)

    def delete_product(self, code: str) -> bool:
        with self._lock:
            clean_code = str(code).strip().lower()
            current_products = self.get_all_products()
            new_list = [p for p in current_products if str(p.get("كود المنتج", "")).strip().lower() != clean_code]
            if len(new_list) < len(current_products):
                return self.save_products(new_list)
            return False

    def create_template(self, target_path: Optional[str] = None) -> str:
        path = Path(target_path) if target_path else self.file_path

        template_items = [
            {
                "كود المنتج": "txxlr",
                "اسم المنتج": "تيشرت قطن رقبة دائرية",
                "السعر": 350,
                "المقاس": "XXL",
                "اللون": "أحمر",
                "الكمية المتاحة": 15,
                "الوصف": "خامة قطيفة ناعمة 100% قطن، تقفيل ممتاز ومريح في اللبس"
            },
            {
                "كود المنتج": "tmlb",
                "اسم المنتج": "تيشرت كاجوال صيفي",
                "السعر": 290,
                "المقاس": "M",
                "اللون": "أزرق",
                "الكمية المتاحة": 8,
                "الوصف": "تيشرت خفيف ومناسب للحر، ألوان ثابتة ضد الغسيل"
            },
            {
                "كود المنتج": "tsg",
                "اسم المنتج": "سويت شيرت شتوي ثقيل",
                "السعر": 550,
                "المقاس": "S",
                "اللون": "رمادي",
                "الكمية المتاحة": 22,
                "الوصف": "سويت شيرت مبطن فرو من الداخل لتدفئة مثالية ومظهر أنيق"
            }
        ]

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Products"
        ws.append(self.columns)
        for item in template_items:
            ws.append([item.get(c, "") for c in self.columns])

        path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(path)
        wb.close()
        logger.info(f"Template created at: {path}")
        return str(path)


excel_cache = ExcelCache(settings.excel_path, settings.excel_reload_interval)