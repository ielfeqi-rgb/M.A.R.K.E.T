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

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'sales',
                    permissions TEXT DEFAULT '[]',
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS port_reservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    port INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    employee_name TEXT NOT NULL,
                    purpose TEXT DEFAULT 'Private Session',
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    released_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS cs_handover_pool (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    customer_phone TEXT NOT NULL,
                    customer_name TEXT DEFAULT '',
                    channel TEXT DEFAULT 'whatsapp',
                    reason TEXT DEFAULT 'تحويل من الذكاء الاصطناعي',
                    last_message TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    assigned_agent_id INTEGER,
                    assigned_agent_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    claimed_at TIMESTAMP,
                    resolved_at TIMESTAMP,
                    FOREIGN KEY (assigned_agent_id) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS scheduled_triggers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    customer_uid TEXT DEFAULT '',
                    customer_phone TEXT DEFAULT '',
                    customer_name TEXT DEFAULT '',
                    trigger_type TEXT NOT NULL,
                    scheduled_for TIMESTAMP NOT NULL,
                    payload_json TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'pending',
                    created_by TEXT DEFAULT 'system',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    executed_at TIMESTAMP,
                    result_json TEXT DEFAULT '{}',
                    error_message TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS customer_profiles (
                    customer_uid TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    identifier TEXT NOT NULL,
                    customer_name TEXT DEFAULT '',
                    customer_phone TEXT DEFAULT '',
                    classification TEXT DEFAULT 'new',
                    first_contact_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_contact_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_messages INTEGER DEFAULT 1,
                    total_orders INTEGER DEFAULT 0,
                    notes TEXT DEFAULT '',
                    metadata_json TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS competitors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    maps_url TEXT NOT NULL,
                    category TEXT DEFAULT '',
                    address TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS competitor_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    competitor_id INTEGER NOT NULL,
                    rating REAL DEFAULT 0.0,
                    total_reviews_count INTEGER DEFAULT 0,
                    rating_delta REAL DEFAULT 0.0,
                    reviews_delta INTEGER DEFAULT 0,
                    sentiment_summary_json TEXT DEFAULT '{}',
                    raw_data_json TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (competitor_id) REFERENCES competitors(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS competitor_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    competitor_id INTEGER NOT NULL,
                    snapshot_id INTEGER NOT NULL,
                    author TEXT DEFAULT 'Anonymous',
                    rating INTEGER DEFAULT 0,
                    text TEXT DEFAULT '',
                    date_text TEXT DEFAULT '',
                    sentiment TEXT DEFAULT 'neutral',
                    keywords_json TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (competitor_id) REFERENCES competitors(id) ON DELETE CASCADE,
                    FOREIGN KEY (snapshot_id) REFERENCES competitor_snapshots(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS competitor_photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    competitor_id INTEGER NOT NULL,
                    snapshot_id INTEGER NOT NULL,
                    remote_url TEXT DEFAULT '',
                    local_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (competitor_id) REFERENCES competitors(id) ON DELETE CASCADE,
                    FOREIGN KEY (snapshot_id) REFERENCES competitor_snapshots(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS competitor_strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    target_competitors_json TEXT DEFAULT '[]',
                    strategy_markdown TEXT NOT NULL,
                    raw_prompt TEXT DEFAULT '',
                    model_used TEXT DEFAULT 'local',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
                CREATE INDEX IF NOT EXISTS idx_orders_phone ON orders(customer_phone);
                CREATE INDEX IF NOT EXISTS idx_logs_session ON conversation_logs(session_id);
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_port_status ON port_reservations(status);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_active_port_unique ON port_reservations(port) WHERE status = 'active';
                CREATE INDEX IF NOT EXISTS idx_cs_pool_status ON cs_handover_pool(status);
                CREATE INDEX IF NOT EXISTS idx_cs_pool_session ON cs_handover_pool(session_id);
                CREATE INDEX IF NOT EXISTS idx_sched_status_date ON scheduled_triggers(status, scheduled_for);
                CREATE INDEX IF NOT EXISTS idx_sched_session ON scheduled_triggers(session_id);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_cust_platform_ident ON customer_profiles(platform, identifier);
                CREATE INDEX IF NOT EXISTS idx_cust_classification ON customer_profiles(classification);
                CREATE INDEX IF NOT EXISTS idx_cust_first_contact ON customer_profiles(first_contact_at);
                CREATE INDEX IF NOT EXISTS idx_comp_active ON competitors(is_active);
                CREATE INDEX IF NOT EXISTS idx_comp_snap_comp ON competitor_snapshots(competitor_id);
                CREATE INDEX IF NOT EXISTS idx_comp_rev_comp ON competitor_reviews(competitor_id);
                CREATE INDEX IF NOT EXISTS idx_comp_rev_sent ON competitor_reviews(sentiment);
                CREATE INDEX IF NOT EXISTS idx_comp_strat_date ON competitor_strategies(created_at);
            """)

            # Safe column migrations for existing databases
            migrations = [
                ("conversation_logs", "customer_uid", "TEXT DEFAULT ''"),
                ("cs_handover_pool", "customer_uid", "TEXT DEFAULT ''"),
                ("cs_handover_pool", "classification", "TEXT DEFAULT 'new'"),
                ("orders", "customer_uid", "TEXT DEFAULT ''"),
                ("scheduled_triggers", "customer_uid", "TEXT DEFAULT ''")
            ]
            for tbl, col, col_type in migrations:
                try:
                    conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_type};")
                except sqlite3.OperationalError:
                    pass # Column already exists

            conn.commit()
            self._seed_default_users(conn)
            logger.info("SQLite WAL Storage Engine with RBAC, Ports, CS Pool, Scheduler & Customer Profiles initialized successfully.")

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

    def _seed_default_users(self, conn: sqlite3.Connection):
        """Seed default admin, IT, sales, and CS users if missing."""
        from auth import hash_password, get_default_permissions_for_role
        import json

        default_users = [
            {
                "username": "admin",
                "password": "admin123",
                "full_name": "المدير العام",
                "role": "admin"
            },
            {
                "username": "it_admin",
                "password": "it123",
                "full_name": "مسؤول الـ IT والدعم الفني",
                "role": "it"
            },
            {
                "username": "sales1",
                "password": "sales123",
                "full_name": "أحمد - موظف مبيعات",
                "role": "sales"
            },
            {
                "username": "cs1",
                "password": "cs123",
                "full_name": "سارة - موظفة خدمة العملاء",
                "role": "cs"
            }
        ]

        for u in default_users:
            perms = get_default_permissions_for_role(u["role"])
            pw_hash = hash_password(u["password"])
            conn.execute("""
                INSERT OR IGNORE INTO users (username, password_hash, full_name, role, permissions, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (u["username"], pw_hash, u["full_name"], u["role"], json.dumps(perms, ensure_ascii=False)))
        conn.commit()
        logger.info("Default seed accounts (admin, it_admin, sales1, cs1) created successfully.")

    # ------------------ User Management & RBAC ------------------ #
    def create_user(self, username: str, password: str, full_name: str, role: str = "sales", permissions: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create new user account."""
        import json
        from auth import hash_password, get_default_permissions_for_role

        clean_username = username.strip().lower()
        if not clean_username or not password:
            return {"success": False, "error": "Username and password are required"}

        if permissions is None:
            permissions = get_default_permissions_for_role(role)

        pw_hash = hash_password(password)
        with self.get_connection() as conn:
            try:
                cursor = conn.execute("""
                    INSERT INTO users (username, password_hash, full_name, role, permissions, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                """, (clean_username, pw_hash, full_name.strip(), role, json.dumps(permissions, ensure_ascii=False)))
                conn.commit()
                return {"success": True, "id": cursor.lastrowid, "username": clean_username, "full_name": full_name, "role": role}
            except sqlite3.IntegrityError:
                return {"success": False, "error": "اسم المستخدم موجود مسبقاً"}
            except Exception as e:
                return {"success": False, "error": str(e)}

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials and return user info dict with session token."""
        import json
        from auth import verify_password, generate_session_token

        clean_username = username.strip().lower()
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM users WHERE username = ? AND is_active = 1", (clean_username,))
            user = cursor.fetchone()
            if not user:
                return None

            user_dict = dict(user)
            if not verify_password(password, user_dict["password_hash"]):
                return None

            # Generate session token
            token = generate_session_token()
            conn.execute("""
                INSERT INTO user_sessions (token, user_id)
                VALUES (?, ?)
            """, (token, user_dict["id"]))
            conn.commit()

            try:
                perms = json.loads(user_dict.get("permissions", "[]"))
            except Exception:
                perms = []

            return {
                "token": token,
                "user": {
                    "id": user_dict["id"],
                    "username": user_dict["username"],
                    "full_name": user_dict["full_name"],
                    "role": user_dict["role"],
                    "permissions": perms,
                    "created_at": user_dict["created_at"]
                }
            }

    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Fetch user by active session token."""
        import json
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT u.id, u.username, u.full_name, u.role, u.permissions, u.is_active, u.created_at
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.token = ? AND u.is_active = 1
            """, (token,))
            row = cursor.fetchone()
            if not row:
                return None
            user_dict = dict(row)
            try:
                user_dict["permissions"] = json.loads(user_dict.get("permissions", "[]"))
            except Exception:
                user_dict["permissions"] = []
            return user_dict

    def delete_session(self, token: str) -> bool:
        """Logout / invalidate session token."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
            conn.commit()
            return True

    def list_users(self) -> List[Dict[str, Any]]:
        """List all registered users without password hashes."""
        import json
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT id, username, full_name, role, permissions, is_active, created_at, updated_at FROM users ORDER BY id ASC")
            users = []
            for r in cursor.fetchall():
                u = dict(r)
                try:
                    u["permissions"] = json.loads(u.get("permissions", "[]"))
                except Exception:
                    u["permissions"] = []
                users.append(u)
            return users

    def update_user(self, user_id: int, full_name: Optional[str] = None, role: Optional[str] = None, permissions: Optional[List[str]] = None, password: Optional[str] = None, is_active: Optional[int] = None) -> Dict[str, Any]:
        """Update user properties and permissions."""
        import json
        from auth import hash_password
        with self.get_connection() as conn:
            try:
                fields = []
                params = []
                if full_name is not None:
                    fields.append("full_name = ?")
                    params.append(full_name.strip())
                if role is not None:
                    fields.append("role = ?")
                    params.append(role)
                if permissions is not None:
                    fields.append("permissions = ?")
                    params.append(json.dumps(permissions, ensure_ascii=False))
                if password:
                    fields.append("password_hash = ?")
                    params.append(hash_password(password))
                if is_active is not None:
                    fields.append("is_active = ?")
                    params.append(int(is_active))

                if not fields:
                    return {"success": True}

                fields.append("updated_at = CURRENT_TIMESTAMP")
                params.append(user_id)

                sql = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
                conn.execute(sql, params)
                conn.commit()
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}

    def delete_user(self, user_id: int) -> Dict[str, Any]:
        """Delete user account."""
        with self.get_connection() as conn:
            try:
                conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}

    # ------------------ Port Reservation Management ------------------ #
    def reserve_port(self, port: int, user_id: int, employee_name: str, purpose: str = "Private Session") -> Dict[str, Any]:
        """Reserve a specific port for an employee session."""
        with self.get_connection() as conn:
            try:
                # Check if port is already actively reserved
                chk = conn.execute("SELECT id, employee_name FROM port_reservations WHERE port = ? AND status = 'active'", (port,)).fetchone()
                if chk:
                    return {"success": False, "error": f"المنفذ {port} محجوز حالياً للموظف: {chk['employee_name']}"}

                cursor = conn.execute("""
                    INSERT INTO port_reservations (port, user_id, employee_name, purpose, status)
                    VALUES (?, ?, ?, ?, 'active')
                """, (port, user_id, employee_name, purpose))
                conn.commit()
                return {
                    "success": True,
                    "reservation_id": cursor.lastrowid,
                    "port": port,
                    "employee_name": employee_name,
                    "purpose": purpose,
                    "status": "active"
                }
            except Exception as e:
                conn.rollback()
                return {"success": False, "error": str(e)}

    def release_port(self, port_or_id: int) -> Dict[str, Any]:
        """Release an active port reservation."""
        with self.get_connection() as conn:
            try:
                cursor = conn.execute("""
                    UPDATE port_reservations
                    SET status = 'released', released_at = CURRENT_TIMESTAMP
                    WHERE (id = ? OR port = ?) AND status = 'active'
                """, (port_or_id, port_or_id))
                conn.commit()
                if cursor.rowcount > 0:
                    return {"success": True, "message": "تم تحرير المنفذ بنجاح"}
                return {"success": False, "error": "المنفذ ليس محجوزاً أو تم تحريره مسبقاً"}
            except Exception as e:
                conn.rollback()
                return {"success": False, "error": str(e)}

    def list_port_reservations(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """List all active or past port reservations."""
        with self.get_connection() as conn:
            if active_only:
                cursor = conn.execute("""
                    SELECT r.*, u.username
                    FROM port_reservations r
                    LEFT JOIN users u ON r.user_id = u.id
                    WHERE r.status = 'active'
                    ORDER BY r.created_at DESC
                """)
            else:
                cursor = conn.execute("""
                    SELECT r.*, u.username
                    FROM port_reservations r
                    LEFT JOIN users u ON r.user_id = u.id
                    ORDER BY r.created_at DESC
                    LIMIT 50
                """)
            return [dict(row) for row in cursor.fetchall()]

    def log_conversation(self, session_id: str, channel: str, user_msg: str, bot_reply: str, latency_ms: int = 0, provider: str = "local", customer_uid: Optional[str] = None):
        """Logs chat turns asynchronously to database with persistent customer_uid."""
        try:
            # Auto-resolve customer_uid if not provided
            if not customer_uid:
                cust = self.get_or_create_customer(platform=channel, identifier=session_id)
                customer_uid = cust.get("customer_uid", "")

            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO conversation_logs (session_id, channel, user_message, bot_reply, latency_ms, provider, customer_uid)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (session_id, channel, user_msg, bot_reply, latency_ms, provider, customer_uid))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log conversation: {e}")

    # ------------------ Global CS Handover Pool Management ------------------ #
    def add_to_cs_pool(
        self,
        session_id: str,
        customer_phone: str,
        customer_name: str = "",
        channel: str = "whatsapp",
        reason: str = "تحويل من الذكاء الاصطناعي",
        last_message: str = "",
        customer_uid: Optional[str] = None
    ) -> Dict[str, Any]:
        """Push a customer conversation turn into the global CS handover pool with persistent UID."""
        if not customer_uid:
            cust = self.get_or_create_customer(platform=channel, identifier=customer_phone or session_id, customer_name=customer_name, customer_phone=customer_phone)
            customer_uid = cust.get("customer_uid", "")
            classification = cust.get("classification", "new")
        else:
            cust = self.get_customer_by_uid(customer_uid)
            classification = cust.get("classification", "new") if cust else "new"

        with self.get_connection() as conn:
            try:
                # If there is already an active pending or claimed handover for this session, update it
                chk = conn.execute("SELECT id, status, assigned_agent_name FROM cs_handover_pool WHERE session_id = ? AND status IN ('pending', 'claimed')", (session_id,)).fetchone()
                if chk:
                    conn.execute("""
                        UPDATE cs_handover_pool
                        SET last_message = ?, reason = ?, customer_uid = ?, classification = ?
                        WHERE id = ?
                    """, (last_message, reason, customer_uid, classification, chk["id"]))
                    conn.commit()
                    return {
                        "success": True,
                        "id": chk["id"],
                        "status": chk["status"],
                        "customer_uid": customer_uid,
                        "classification": classification,
                        "updated": True
                    }

                cursor = conn.execute("""
                    INSERT INTO cs_handover_pool (session_id, customer_phone, customer_name, channel, reason, last_message, status, customer_uid, classification)
                    VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """, (session_id, customer_phone, customer_name, channel, reason, last_message, customer_uid, classification))
                conn.commit()
                return {
                    "success": True,
                    "id": cursor.lastrowid,
                    "session_id": session_id,
                    "customer_phone": customer_phone,
                    "customer_name": customer_name,
                    "customer_uid": customer_uid,
                    "classification": classification,
                    "status": "pending"
                }
            except Exception as e:
                conn.rollback()
                logger.error(f"Error adding to CS pool: {e}")
                return {"success": False, "error": str(e)}

    def list_cs_pool(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List handover conversations in the CS Pool."""
        with self.get_connection() as conn:
            if status_filter:
                cursor = conn.execute("""
                    SELECT * FROM cs_handover_pool
                    WHERE status = ?
                    ORDER BY created_at DESC
                """, (status_filter,))
            else:
                cursor = conn.execute("""
                    SELECT * FROM cs_handover_pool
                    WHERE status IN ('pending', 'claimed')
                    ORDER BY CASE WHEN status = 'pending' THEN 0 ELSE 1 END, created_at DESC
                """)
            return [dict(r) for r in cursor.fetchall()]

    def claim_cs_conversation(self, handover_id: int, agent_id: int, agent_name: str) -> Dict[str, Any]:
        """Claim a conversation exclusively by a CS agent."""
        with self.get_connection() as conn:
            try:
                chk = conn.execute("SELECT status, assigned_agent_name FROM cs_handover_pool WHERE id = ?", (handover_id,)).fetchone()
                if not chk:
                    return {"success": False, "error": "المحادثة غير موجودة في البوول"}
                if chk["status"] == "claimed" and chk["assigned_agent_name"] != agent_name:
                    return {"success": False, "error": f"المحادثة مستلمة بالفعل بواسطة: {chk['assigned_agent_name']}"}

                conn.execute("""
                    UPDATE cs_handover_pool
                    SET status = 'claimed', assigned_agent_id = ?, assigned_agent_name = ?, claimed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (agent_id, agent_name, handover_id))
                conn.commit()
                return {"success": True, "message": f"تم استلام المحادثة بنجاح بواسطة {agent_name}"}
            except Exception as e:
                conn.rollback()
                return {"success": False, "error": str(e)}

    def resolve_cs_conversation(self, handover_id: int) -> Dict[str, Any]:
        """Resolve handover and return conversation back to AI automation."""
        with self.get_connection() as conn:
            try:
                conn.execute("""
                    UPDATE cs_handover_pool
                    SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (handover_id,))
                conn.commit()
                return {"success": True, "message": "تم إنهاء التدخل البشري وإعادة المحادثة للذكاء الاصطناعي بنجاح"}
            except Exception as e:
                conn.rollback()
                return {"success": False, "error": str(e)}

    # ------------------ Time & Delay Scheduler Methods ------------------ #
    def add_scheduled_trigger(
        self,
        session_id: str,
        customer_phone: str,
        customer_name: str,
        trigger_type: str,
        scheduled_for: str,
        payload: Dict[str, Any],
        created_by: str = "system"
    ) -> Dict[str, Any]:
        """Insert a scheduled trigger/delayed task."""
        import json
        with self.get_connection() as conn:
            try:
                cursor = conn.execute("""
                    INSERT INTO scheduled_triggers (
                        session_id, customer_phone, customer_name, trigger_type,
                        scheduled_for, payload_json, status, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                """, (
                    session_id, customer_phone, customer_name, trigger_type,
                    scheduled_for, json.dumps(payload, ensure_ascii=False), created_by
                ))
                conn.commit()
                return {
                    "success": True,
                    "id": cursor.lastrowid,
                    "session_id": session_id,
                    "customer_phone": customer_phone,
                    "scheduled_for": scheduled_for,
                    "trigger_type": trigger_type,
                    "status": "pending"
                }
            except Exception as e:
                conn.rollback()
                logger.error(f"Error adding scheduled trigger: {e}")
                return {"success": False, "error": str(e)}

    def get_due_scheduled_triggers(self) -> List[Dict[str, Any]]:
        """Fetch all pending triggers whose scheduled_for time is in the past or now."""
        import json
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM scheduled_triggers
                WHERE status = 'pending' AND datetime(scheduled_for) <= datetime('now', 'localtime')
                ORDER BY scheduled_for ASC
            """)
            items = []
            for r in cursor.fetchall():
                d = dict(r)
                try:
                    d["payload"] = json.loads(d.get("payload_json") or "{}")
                except Exception:
                    d["payload"] = {}
                items.append(d)
            return items

    def mark_trigger_status(
        self,
        trigger_id: int,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error_message: str = ""
    ) -> bool:
        """Mark a trigger completed, failed, or cancelled."""
        import json
        with self.get_connection() as conn:
            try:
                conn.execute("""
                    UPDATE scheduled_triggers
                    SET status = ?, executed_at = CURRENT_TIMESTAMP, result_json = ?, error_message = ?
                    WHERE id = ?
                """, (status, json.dumps(result or {}, ensure_ascii=False), error_message, trigger_id))
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                logger.error(f"Error updating trigger status: {e}")
                return False

    def cancel_scheduled_trigger(self, trigger_id: int) -> Dict[str, Any]:
        """Cancel a pending trigger."""
        with self.get_connection() as conn:
            try:
                chk = conn.execute("SELECT status FROM scheduled_triggers WHERE id = ?", (trigger_id,)).fetchone()
                if not chk:
                    return {"success": False, "error": "المهمة المجدولة غير موجودة"}
                if chk["status"] != "pending":
                    return {"success": False, "error": f"المهمة ليست في حالة انتظار ({chk['status']})"}

                conn.execute("UPDATE scheduled_triggers SET status = 'cancelled' WHERE id = ?", (trigger_id,))
                conn.commit()
                return {"success": True, "message": "تم إلغاء المهمة المجدولة بنجاح"}
            except Exception as e:
                conn.rollback()
                return {"success": False, "error": str(e)}

    def list_scheduled_triggers(self, status_filter: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List scheduled triggers for IT/admin monitoring."""
        import json
        with self.get_connection() as conn:
            if status_filter and status_filter != "all":
                cursor = conn.execute("""
                    SELECT * FROM scheduled_triggers
                    WHERE status = ?
                    ORDER BY scheduled_for DESC
                    LIMIT ?
                """, (status_filter, limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM scheduled_triggers
                    ORDER BY CASE WHEN status = 'pending' THEN 0 ELSE 1 END, scheduled_for DESC
                    LIMIT ?
                """, (limit,))

            items = []
            for r in cursor.fetchall():
                d = dict(r)
                try:
                    d["payload"] = json.loads(d.get("payload_json") or "{}")
                except Exception:
                    d["payload"] = {}
                try:
                    d["result"] = json.loads(d.get("result_json") or "{}")
                except Exception:
                    d["result"] = {}
                items.append(d)
            return items

    def get_scheduled_trigger_by_id(self, trigger_id: int) -> Optional[Dict[str, Any]]:
        """Get single trigger by id."""
        import json
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM scheduled_triggers WHERE id = ?", (trigger_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["payload"] = json.loads(d.get("payload_json") or "{}")
            except Exception:
                d["payload"] = {}
            return d

    # ------------------ Customer Composite UID & Classification ------------------ #
    def get_or_create_customer(
        self,
        platform: str,
        identifier: str,
        customer_name: str = "",
        customer_phone: str = ""
    ) -> Dict[str, Any]:
        """
        Retrieves an existing customer profile or creates a new one with a persistent Composite UID:
        Format: {PLATFORM}_{IDENTIFIER}_{FIRST_CONTACT_TIMESTAMP}
        e.g., WA_01012345678_20260920_151754
        """
        import re
        import json

        norm_platform = (platform or "whatsapp").lower().strip()
        norm_ident = str(identifier or "").strip()
        if not norm_ident:
            norm_ident = str(customer_phone or "guest").strip()

        clean_ident = re.sub(r'[^a-zA-Z0-9_\u0600-\u06FF]', '', norm_ident) or "client"

        with self.get_connection() as conn:
            try:
                # Check if customer already exists for this (platform, identifier)
                row = conn.execute("""
                    SELECT * FROM customer_profiles
                    WHERE platform = ? AND identifier = ?
                """, (norm_platform, norm_ident)).fetchone()

                if row:
                    cust = dict(row)
                    # Increment message count & update last contact
                    new_msgs = cust.get("total_messages", 1) + 1
                    current_class = cust.get("classification", "new")
                    
                    # Auto classification upgrade: if 3+ messages and still 'new' -> upgrade to 'returning'
                    if new_msgs >= 3 and current_class == "new":
                        current_class = "returning"

                    update_name = customer_name.strip() if customer_name else cust.get("customer_name", "")
                    update_phone = customer_phone.strip() if customer_phone else cust.get("customer_phone", "")

                    conn.execute("""
                        UPDATE customer_profiles
                        SET last_contact_at = CURRENT_TIMESTAMP,
                            total_messages = ?,
                            classification = ?,
                            customer_name = ?,
                            customer_phone = ?
                        WHERE customer_uid = ?
                    """, (new_msgs, current_class, update_name, update_phone, cust["customer_uid"]))
                    conn.commit()

                    cust["total_messages"] = new_msgs
                    cust["classification"] = current_class
                    cust["customer_name"] = update_name
                    cust["customer_phone"] = update_phone
                    return cust

                # New Customer: Generate Persistent Composite UID with first contact timestamp
                prefix = "WA" if "what" in norm_platform else "FB" if "face" in norm_platform or "meta" in norm_platform else "TG" if "tele" in norm_platform else "WEB"
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                customer_uid = f"{prefix}_{clean_ident}_{ts}"

                conn.execute("""
                    INSERT INTO customer_profiles (
                        customer_uid, platform, identifier, customer_name, customer_phone,
                        classification, first_contact_at, last_contact_at, total_messages, total_orders
                    ) VALUES (?, ?, ?, ?, ?, 'new', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, 0)
                """, (customer_uid, norm_platform, norm_ident, customer_name, customer_phone or norm_ident))
                conn.commit()

                logger.info(f"Generated new Persistent Customer UID: {customer_uid} for {norm_platform}:{norm_ident}")

                return {
                    "customer_uid": customer_uid,
                    "platform": norm_platform,
                    "identifier": norm_ident,
                    "customer_name": customer_name,
                    "customer_phone": customer_phone or norm_ident,
                    "classification": "new",
                    "total_messages": 1,
                    "total_orders": 0,
                    "first_contact_at": datetime.now().isoformat()
                }
            except Exception as e:
                conn.rollback()
                logger.error(f"Error in get_or_create_customer: {e}")
                # Fallback non-blocking
                return {
                    "customer_uid": f"TEMP_{clean_ident}_{int(datetime.now().timestamp())}",
                    "platform": norm_platform,
                    "identifier": norm_ident,
                    "classification": "new"
                }

    def get_customer_by_uid(self, customer_uid: str) -> Optional[Dict[str, Any]]:
        """Fetch customer profile by unique composite UID."""
        import json
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM customer_profiles WHERE customer_uid = ?", (customer_uid,)).fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["metadata"] = json.loads(d.get("metadata_json") or "{}")
            except Exception:
                d["metadata"] = {}
            return d

    def update_customer_classification(self, customer_uid: str, classification: str, notes: str = "") -> Dict[str, Any]:
        """Update customer classification (e.g., 'new', 'returning', 'vip', 'lead', 'cs_ticket')."""
        with self.get_connection() as conn:
            try:
                chk = conn.execute("SELECT customer_uid FROM customer_profiles WHERE customer_uid = ?", (customer_uid,)).fetchone()
                if not chk:
                    return {"success": False, "error": "العميل غير موجود"}

                conn.execute("""
                    UPDATE customer_profiles
                    SET classification = ?, notes = CASE WHEN ? != '' THEN ? ELSE notes END
                    WHERE customer_uid = ?
                """, (classification, notes, notes, customer_uid))
                
                # Also update active CS tickets classification
                conn.execute("UPDATE cs_handover_pool SET classification = ? WHERE customer_uid = ?", (classification, customer_uid))
                conn.commit()
                return {"success": True, "customer_uid": customer_uid, "classification": classification}
            except Exception as e:
                conn.rollback()
                return {"success": False, "error": str(e)}

    def list_customers(
        self,
        classification_filter: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List all registered customers with their composite UIDs and classifications."""
        import json
        with self.get_connection() as conn:
            query = "SELECT * FROM customer_profiles WHERE 1=1"
            params = []

            if classification_filter and classification_filter != "all":
                query += " AND classification = ?"
                params.append(classification_filter)

            if search:
                query += " AND (customer_uid LIKE ? OR customer_name LIKE ? OR customer_phone LIKE ? OR identifier LIKE ?)"
                like_term = f"%{search}%"
                params.extend([like_term, like_term, like_term, like_term])

            query += " ORDER BY last_contact_at DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, tuple(params))
            items = []
            for r in cursor.fetchall():
                d = dict(r)
                try:
                    d["metadata"] = json.loads(d.get("metadata_json") or "{}")
                except Exception:
                    d["metadata"] = {}
                items.append(d)
            return items

    def get_customer_full_history(self, customer_uid: str) -> Dict[str, Any]:
        """Returns customer profile + all conversation turns + orders + handover tickets."""
        profile = self.get_customer_by_uid(customer_uid)
        if not profile:
            return {"success": False, "error": "العميل غير موجود"}

        with self.get_connection() as conn:
            # 1. Conversation logs
            logs_cursor = conn.execute("""
                SELECT * FROM conversation_logs
                WHERE customer_uid = ? OR session_id = ?
                ORDER BY created_at ASC
            """, (customer_uid, profile.get("identifier", "")))
            logs = [dict(r) for r in logs_cursor.fetchall()]

            # 2. Orders
            orders_cursor = conn.execute("""
                SELECT * FROM orders
                WHERE customer_uid = ? OR customer_phone = ?
                ORDER BY created_at DESC
            """, (customer_uid, profile.get("customer_phone", "")))
            orders = [dict(r) for r in orders_cursor.fetchall()]

            # 3. Handover tickets
            tickets_cursor = conn.execute("""
                SELECT * FROM cs_handover_pool
                WHERE customer_uid = ? OR session_id = ?
                ORDER BY created_at DESC
            """, (customer_uid, profile.get("identifier", "")))
            tickets = [dict(r) for r in tickets_cursor.fetchall()]

            return {
                "success": True,
                "profile": profile,
                "logs_count": len(logs),
                "logs": logs,
                "orders_count": len(orders),
                "orders": orders,
                "tickets_count": len(tickets),
                "tickets": tickets
            }

    # ================================================================
    # M.A.R.K.E.T AI v4.0.5 - Competitor Intelligence Methods
    # ================================================================

    def add_competitor(self, name: str, maps_url: str, category: str = "", address: str = "", phone: str = "") -> Dict[str, Any]:
        """Registers a new competitor to track."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO competitors (name, maps_url, category, address, phone, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (name.strip(), maps_url.strip(), category.strip(), address.strip(), phone.strip()))
            conn.commit()
            return {"success": True, "id": cursor.lastrowid, "name": name}

    def list_competitors(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Lists tracked competitors along with their latest snapshot metrics."""
        with self.get_connection() as conn:
            query = """
                SELECT c.*, 
                       s.rating AS latest_rating,
                       s.total_reviews_count AS latest_reviews_count,
                       s.rating_delta,
                       s.reviews_delta,
                       s.sentiment_summary_json,
                       s.created_at AS last_scraped_at
                FROM competitors c
                LEFT JOIN competitor_snapshots s ON s.id = (
                    SELECT id FROM competitor_snapshots 
                    WHERE competitor_id = c.id 
                    ORDER BY created_at DESC LIMIT 1
                )
            """
            if active_only:
                query += " WHERE c.is_active = 1"
            query += " ORDER BY c.id DESC"

            cursor = conn.execute(query)
            competitors = []
            import json
            for r in cursor.fetchall():
                d = dict(r)
                try:
                    d["sentiment_summary"] = json.loads(d.get("sentiment_summary_json") or "{}")
                except Exception:
                    d["sentiment_summary"] = {}
                competitors.append(d)
            return competitors

    def get_competitor(self, competitor_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves competitor details, snapshots, recent reviews, and photos."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM competitors WHERE id = ?", (competitor_id,))
            row = cursor.fetchone()
            if not row:
                return None
            comp = dict(row)

            # Latest snapshot
            snap_cursor = conn.execute("""
                SELECT * FROM competitor_snapshots 
                WHERE competitor_id = ? 
                ORDER BY created_at DESC LIMIT 1
            """, (competitor_id,))
            snap_row = snap_cursor.fetchone()
            import json
            comp["latest_snapshot"] = dict(snap_row) if snap_row else None
            if comp["latest_snapshot"]:
                try:
                    comp["latest_snapshot"]["sentiment_summary"] = json.loads(comp["latest_snapshot"].get("sentiment_summary_json") or "{}")
                except Exception:
                    comp["latest_snapshot"]["sentiment_summary"] = {}

            # Recent reviews (up to 30)
            rev_cursor = conn.execute("""
                SELECT * FROM competitor_reviews 
                WHERE competitor_id = ? 
                ORDER BY id DESC LIMIT 30
            """, (competitor_id,))
            reviews = []
            for r in rev_cursor.fetchall():
                rd = dict(r)
                try:
                    rd["keywords"] = json.loads(rd.get("keywords_json") or "[]")
                except Exception:
                    rd["keywords"] = []
                reviews.append(rd)
            comp["reviews"] = reviews

            # Photos
            photo_cursor = conn.execute("""
                SELECT * FROM competitor_photos 
                WHERE competitor_id = ? 
                ORDER BY id DESC LIMIT 15
            """, (competitor_id,))
            comp["photos"] = [dict(p) for p in photo_cursor.fetchall()]

            # Historical snapshots for trend chart
            history_cursor = conn.execute("""
                SELECT id, rating, total_reviews_count, rating_delta, reviews_delta, created_at
                FROM competitor_snapshots
                WHERE competitor_id = ?
                ORDER BY created_at ASC
            """, (competitor_id,))
            comp["history"] = [dict(h) for h in history_cursor.fetchall()]

            return comp

    def delete_competitor(self, competitor_id: int) -> Dict[str, Any]:
        """Deletes a competitor and associated snapshots/reviews."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM competitors WHERE id = ?", (competitor_id,))
            conn.commit()
            return {"success": True, "id": competitor_id}

    def save_competitor_snapshot(self, competitor_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Saves a scraped snapshot, calculates Delta Trends from previous snapshot,
        and saves parsed reviews and local photos.
        """
        import json
        with self.get_connection() as conn:
            # 1. Fetch previous snapshot for Delta calculation
            prev_cursor = conn.execute("""
                SELECT rating, total_reviews_count FROM competitor_snapshots
                WHERE competitor_id = ?
                ORDER BY created_at DESC LIMIT 1
            """, (competitor_id,))
            prev_row = prev_cursor.fetchone()

            current_rating = float(data.get("rating", 0.0))
            current_reviews_count = int(data.get("total_reviews_count", 0))

            rating_delta = 0.0
            reviews_delta = 0

            if prev_row:
                prev_rating = float(prev_row["rating"] or 0.0)
                prev_reviews = int(prev_row["total_reviews_count"] or 0)
                rating_delta = round(current_rating - prev_rating, 2)
                reviews_delta = current_reviews_count - prev_reviews

            # 2. Update competitor name/address/category if scraped
            if data.get("competitor_name"):
                conn.execute("""
                    UPDATE competitors 
                    SET name = COALESCE(NULLIF(?, ''), name),
                        address = COALESCE(NULLIF(?, ''), address),
                        category = COALESCE(NULLIF(?, ''), category),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (data.get("competitor_name"), data.get("address", ""), data.get("category", ""), competitor_id))

            # 3. Insert Snapshot
            sentiment_json = json.dumps(data.get("sentiment_summary", {}), ensure_ascii=False)
            raw_json = json.dumps(data, ensure_ascii=False)

            snap_cursor = conn.execute("""
                INSERT INTO competitor_snapshots (
                    competitor_id, rating, total_reviews_count, rating_delta, reviews_delta,
                    sentiment_summary_json, raw_data_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (competitor_id, current_rating, current_reviews_count, rating_delta, reviews_delta, sentiment_json, raw_json))
            snapshot_id = snap_cursor.lastrowid

            # 4. Insert Reviews
            for rev in data.get("reviews", []):
                kw_json = json.dumps(rev.get("keywords", []), ensure_ascii=False)
                conn.execute("""
                    INSERT INTO competitor_reviews (
                        competitor_id, snapshot_id, author, rating, text, date_text, sentiment, keywords_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    competitor_id,
                    snapshot_id,
                    rev.get("author", "Anonymous"),
                    int(rev.get("rating", 0)),
                    rev.get("text", ""),
                    rev.get("date_text", ""),
                    rev.get("sentiment", "neutral"),
                    kw_json
                ))

            # 5. Insert Photos
            for p in data.get("local_photos", []):
                conn.execute("""
                    INSERT INTO competitor_photos (competitor_id, snapshot_id, remote_url, local_path)
                    VALUES (?, ?, ?, ?)
                """, (competitor_id, snapshot_id, "", p))

            conn.commit()
            return {
                "success": True,
                "snapshot_id": snapshot_id,
                "rating_delta": rating_delta,
                "reviews_delta": reviews_delta
            }

    def save_strategic_analysis(self, title: str, target_competitors: List[int], strategy_markdown: str, raw_prompt: str = "", model_used: str = "local") -> Dict[str, Any]:
        """Saves an AI-generated competitive strategy report."""
        import json
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO competitor_strategies (title, target_competitors_json, strategy_markdown, raw_prompt, model_used, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (title, json.dumps(target_competitors), strategy_markdown, raw_prompt, model_used))
            conn.commit()
            return {"success": True, "strategy_id": cursor.lastrowid}

    def list_strategic_analyses(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Lists saved strategic intelligence analysis reports."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM competitor_strategies ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            items = []
            import json
            for r in cursor.fetchall():
                d = dict(r)
                try:
                    d["target_competitors"] = json.loads(d.get("target_competitors_json") or "[]")
                except Exception:
                    d["target_competitors"] = []
                items.append(d)
            return items


# Global singleton
db = DatabaseManager()


