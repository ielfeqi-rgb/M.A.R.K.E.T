"""
M.A.R.K.E.T AI - Enterprise SQLite WAL Storage Engine
ACID-Compliant, Thread-Safe, Concurrent Edge Database with Auto-Sync for products.xlsx.
"""

import sqlite3
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "market_edge.db"
EXCEL_PATH = Path(__file__).parent / "products.xlsx"

class DatabaseManager:
    """
    Thread-safe SQLite database manager running in WAL (Write-Ahead Logging) mode.
    Guarantees non-blocking concurrent reads and safe atomic checkout operations.
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[Path] = None):
        if self._initialized:
            return
        self.db_path = db_path or DB_PATH
        self._init_db()
        self._initialized = True

    def get_connection(self) -> sqlite3.Connection:
        """
        Creates a dedicated connection tuned for high-concurrency edge workloads.
        """
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        # Enable Write-Ahead Logging (WAL) for concurrent read/write
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA temp_store = MEMORY;")
        conn.execute("PRAGMA mmap_size = 30000000000;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def _init_db(self):
        """Initializes tables and indexes."""
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS products (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    price REAL NOT NULL,
                    size TEXT DEFAULT '',
                    color TEXT DEFAULT '',
                    stock INTEGER NOT NULL DEFAULT 0,
                    description TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_phone TEXT NOT NULL,
                    customer_name TEXT DEFAULT '',
                    channel TEXT DEFAULT 'whatsapp',
                    product_code TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    unit_price REAL NOT NULL,
                    total_price REAL NOT NULL,
                    status TEXT DEFAULT 'confirmed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_code) REFERENCES products(code)
                );

                CREATE TABLE IF NOT EXISTS conversation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    bot_reply TEXT NOT NULL,
                    latency_ms INTEGER DEFAULT 0,
                    provider TEXT DEFAULT 'local',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
                CREATE INDEX IF NOT EXISTS idx_orders_phone ON orders(customer_phone);
                CREATE INDEX IF NOT EXISTS idx_logs_session ON conversation_logs(session_id);
            """)
            conn.commit()
            logger.info("SQLite WAL Storage Engine initialized successfully.")

    def sync_from_excel(self, excel_path: Optional[Path] = None) -> int:
        """
        Populates/syncs SQLite tables from products.xlsx.
        """
        import openpyxl
        path = excel_path or EXCEL_PATH
        if not path.exists():
            return 0

        try:
            wb = openpyxl.load_workbook(str(path), data_only=True)
            sheet = wb.active
            rows = list(sheet.iter_rows(values_only=True))
            wb.close()

            if not rows or len(rows) < 2:
                return 0

            headers = [str(h).strip() if h is not None else "" for h in rows[0]]
            col_map = {
                "كود المنتج": "code",
                "اسم المنتج": "name",
                "السعر": "price",
                "المقاس": "size",
                "اللون": "color",
                "الكمية المتاحة": "stock",
                "الوصف": "description"
            }

            synced_count = 0
            with self.get_connection() as conn:
                for row in rows[1:]:
                    if not any(row):
                        continue
                    row_dict = {}
                    for idx, h in enumerate(headers):
                        if h in col_map and idx < len(row):
                            row_dict[col_map[h]] = row[idx]

                    code = str(row_dict.get("code", "")).strip().lower()
                    if not code:
                        continue

                    name = str(row_dict.get("name", "")).strip()
                    try:
                        price = float(row_dict.get("price", 0) or 0)
                    except (ValueError, TypeError):
                        price = 0.0

                    try:
                        stock = int(row_dict.get("stock", 0) or 0)
                    except (ValueError, TypeError):
                        stock = 0

                    size = str(row_dict.get("size", "") or "")
                    color = str(row_dict.get("color", "") or "")
                    desc = str(row_dict.get("description", "") or "")

                    conn.execute("""
                        INSERT INTO products (code, name, price, size, color, stock, description, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(code) DO UPDATE SET
                            name=excluded.name,
                            price=excluded.price,
                            size=excluded.size,
                            color=excluded.color,
                            stock=excluded.stock,
                            description=excluded.description,
                            updated_at=CURRENT_TIMESTAMP
                    """, (code, name, price, size, color, stock, desc))
                    synced_count += 1
                conn.commit()
            logger.info(f"Synced {synced_count} products from Excel to SQLite WAL database.")
            return synced_count
        except Exception as e:
            logger.error(f"Error syncing from Excel: {e}")
            return 0

    def sync_to_excel(self, excel_path: Optional[Path] = None) -> bool:
        """
        Exports live SQLite database back to products.xlsx.
        """
        import openpyxl
        path = excel_path or EXCEL_PATH
        try:
            products = self.get_all_products()
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Products"

            headers = ["كود المنتج", "اسم المنتج", "السعر", "المقاس", "اللون", "الكمية المتاحة", "الوصف"]
            ws.append(headers)

            for p in products:
                ws.append([
                    p.get("code", ""),
                    p.get("name", ""),
                    p.get("price", 0),
                    p.get("size", ""),
                    p.get("color", ""),
                    p.get("stock", 0),
                    p.get("description", "")
                ])

            path.parent.mkdir(parents=True, exist_ok=True)
            wb.save(str(path))
            wb.close()
            return True
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            return False

    def get_product(self, code: str) -> Optional[Dict[str, Any]]:
        """Fetch single product by code."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM products WHERE code = ?", (code.strip().lower(),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_products(self) -> List[Dict[str, Any]]:
        """Fetch all products."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM products ORDER BY name ASC")
            return [dict(r) for r in cursor.fetchall()]

    def search_products(self, query: str) -> List[Dict[str, Any]]:
        """Fast SQL token search for grounding."""
        term = f"%{query.strip()}%"
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM products
                WHERE name LIKE ? OR code LIKE ? OR description LIKE ? OR color LIKE ?
                LIMIT 5
            """, (term, term, term, term))
            return [dict(r) for r in cursor.fetchall()]

    def atomic_checkout(self, product_code: str, quantity: int, customer_phone: str, customer_name: str = "", channel: str = "whatsapp") -> Dict[str, Any]:
        """
        Atomic checkout preventing race conditions under high concurrent load.
        Uses single-query decrement with conditional check (stock >= quantity).
        """
        clean_code = product_code.strip().lower()
        if quantity <= 0:
            return {"success": False, "error": "Invalid quantity"}

        with self.get_connection() as conn:
            try:
                # 1. Atomic update with stock check
                cursor = conn.execute("""
                    UPDATE products
                    SET stock = stock - ?, updated_at = CURRENT_TIMESTAMP
                    WHERE code = ? AND stock >= ?
                """, (quantity, clean_code, quantity))

                if cursor.rowcount == 0:
                    # Check whether out of stock or product not found
                    chk = conn.execute("SELECT stock FROM products WHERE code = ?", (clean_code,)).fetchone()
                    if not chk:
                        return {"success": False, "error": "Product not found"}
                    return {"success": False, "error": f"Insufficient stock. Available: {chk['stock']}"}

                # 2. Get product price
                p = conn.execute("SELECT price, name FROM products WHERE code = ?", (clean_code,)).fetchone()
                unit_price = float(p["price"]) if p else 0.0
                total_price = unit_price * quantity

                # 3. Insert order record
                conn.execute("""
                    INSERT INTO orders (customer_phone, customer_name, channel, product_code, quantity, unit_price, total_price, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'confirmed')
                """, (customer_phone, customer_name, channel, clean_code, quantity, unit_price, total_price))

                conn.commit()
                return {
                    "success": True,
                    "product_name": p["name"],
                    "product_code": clean_code,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_price": total_price,
                    "status": "confirmed"
                }
            except Exception as e:
                conn.rollback()
                logger.error(f"Atomic checkout transaction error: {e}")
                return {"success": False, "error": str(e)}

    def log_conversation(self, session_id: str, channel: str, user_msg: str, bot_reply: str, latency_ms: int = 0, provider: str = "local"):
        """Logs chat turns asynchronously to database."""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO conversation_logs (session_id, channel, user_message, bot_reply, latency_ms, provider)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, channel, user_msg, bot_reply, latency_ms, provider))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log conversation: {e}")

# Global singleton
db = DatabaseManager()
