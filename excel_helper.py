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

    def search_product_fuzzy(self, user_query: str, min_threshold: float = 0.55) -> Dict[str, Any]:
        """
        Real multi-attribute fuzzy search against Excel catalog.
        Computes mathematical similarity score across Name, Code, Color, Size, and Description.
        Returns: {
            "product": Dict or None,
            "confidence": float,
            "matched_by": str,
            "exact_code_match": bool,
            "stock_available": bool
        }
        """
        import difflib
        import re

        with self._lock:
            if self._cache is None or (time.time() - self._last_load > self.reload_interval):
                if not self.reload():
                    return {"product": None, "confidence": 0.0, "matched_by": "none", "exact_code_match": False, "stock_available": False}

            def normalize_ar(text: str) -> str:
                if not text:
                    return ""
                text = str(text).lower().strip()
                # Normalize common eCommerce spelling variations
                text = text.replace("تيشيرت", "تيشرت").replace("سويت شيرت", "سويتشرت")
                text = re.sub(r'[إأآا]', 'ا', text)
                text = re.sub(r'ة', 'ه', text)
                text = re.sub(r'ى', 'ي', text)
                text = re.sub(r'[^\w\s]', ' ', text)
                words = []
                for w in text.split():
                    # Strip leading 'ال' for root comparison if word length > 3
                    if w.startswith("ال") and len(w) > 3:
                        w = w[2:]
                    words.append(w)
                return " ".join(words)

            clean_query = normalize_ar(user_query)
            
            # Common conversational filler words in Egyptian customer support inquiries
            stopwords = {"السلام", "عليكم", "ورحمه", "الله", "وبركاته", "ازيك", "يا", "فندم", "لو", "سمحت", "بكام", "سعر", "كام", "عايز", "عاوز", "عاوزه", "ممكن", "تفاصيل", "في", "من", "علي", "عندكم", "موجود"}
            meaningful_query_tokens = set([w for w in clean_query.split() if w not in stopwords])
            if not meaningful_query_tokens:
                meaningful_query_tokens = set(clean_query.split())

            best_match = None
            best_score = 0.0
            best_match_by = "none"
            exact_match = False

            for code, product in self._cache.items():
                norm_code = normalize_ar(code)
                norm_name = normalize_ar(product.get("اسم المنتج", ""))
                norm_color = normalize_ar(product.get("اللون", ""))
                norm_size = normalize_ar(product.get("المقاس", ""))
                norm_desc = normalize_ar(product.get("الوصف", ""))

                # 1. Exact Code Match (Confidence 1.0)
                if norm_code and (norm_code == clean_query or norm_code in meaningful_query_tokens):
                    best_match = product
                    best_score = 1.0
                    best_match_by = f"exact_code:{code}"
                    exact_match = True
                    break

                # 2. Token Matching on meaningful product attributes
                all_product_text = f"{norm_name} {norm_color} {norm_size} {norm_desc}"
                product_tokens = set(all_product_text.split())

                # Intersection over meaningful query tokens
                overlap = meaningful_query_tokens.intersection(product_tokens)
                token_recall = len(overlap) / max(len(meaningful_query_tokens), 1)

                # Attribute bonuses: Color match and Size match
                color_bonus = 0.25 if norm_color and norm_color in meaningful_query_tokens else 0.0
                size_bonus = 0.20 if norm_size and norm_size in meaningful_query_tokens else 0.0

                # Name sequence match
                name_tokens = set(norm_name.split())
                name_overlap = meaningful_query_tokens.intersection(name_tokens)
                name_score = len(name_overlap) / max(len(name_tokens), 1)

                # Composite score
                composite_score = round(min(1.0, (token_recall * 0.50) + (name_score * 0.30) + color_bonus + size_bonus), 3)

                if composite_score > best_score:
                    best_score = composite_score
                    best_match = product
                    best_match_by = f"fuzzy_composite:{composite_score}"

            # Check threshold
            if best_score < min_threshold:
                return {
                    "product": None,
                    "confidence": best_score,
                    "matched_by": "below_threshold",
                    "exact_code_match": False,
                    "stock_available": False
                }

            # Check stock availability
            qty_raw = str(best_match.get("الكمية المتاحة", "0")).strip()
            stock_qty = int(qty_raw) if qty_raw.isdigit() else 1
            stock_available = stock_qty > 0

            return {
                "product": best_match,
                "confidence": best_score,
                "matched_by": best_match_by,
                "exact_code_match": exact_match,
                "stock_available": stock_available
            }

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