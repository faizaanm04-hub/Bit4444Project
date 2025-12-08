# -*- encoding: utf-8 -*-
"""
FMZB Hub - Module 2 Product & Inventory data helpers.
Uses PyMySQL with parameterized queries to avoid SQL injection.
"""

import os
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME", "BIT 4444 Group Project")


def get_db():
    """Create and return a new database connection."""
    return pymysql.connect(
        host=os.getenv("DB_HOST", "mysql"),
        port=int(os.getenv("DB_PORT", 3309)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "change-me"),
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )


def sku_exists(sku: str, exclude_product_id: Optional[int] = None) -> bool:
    """Check if a SKU already exists (optionally excluding one product)."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if exclude_product_id:
                cur.execute(
                    "SELECT 1 FROM product WHERE SKU = %s AND product_id <> %s LIMIT 1",
                    (sku, exclude_product_id),
                )
            else:
                cur.execute("SELECT 1 FROM product WHERE SKU = %s LIMIT 1", (sku,))
            return cur.fetchone() is not None
    finally:
        conn.close()


def insert_product(payload: Dict) -> int:
    """Insert a new product and return its primary key."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO product (
                    SKU, title, category, price, quantity,
                    description, image_url, archived, is_sold, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0, NOW(), NOW())
                """,
                (
                    payload.get("SKU"),
                    payload.get("title"),
                    payload.get("category"),
                    Decimal(payload.get("price")),
                    int(payload.get("quantity")),
                    payload.get("description"),
                    payload.get("image_url"),
                ),
            )
            return cur.lastrowid
    finally:
        conn.close()


def fetch_product(product_id: int) -> Optional[Dict]:
    """Return a product by id."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM product WHERE product_id = %s", (product_id,))
            return cur.fetchone()
    finally:
        conn.close()


def update_product(product_id: int, payload: Dict) -> None:
    """Update product fields."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE product
                SET SKU=%s, title=%s, category=%s, price=%s, quantity=%s,
                    description=%s, image_url=%s, updated_at=NOW()
                WHERE product_id=%s
                """,
                (
                    payload.get("SKU"),
                    payload.get("title"),
                    payload.get("category"),
                    Decimal(payload.get("price")),
                    int(payload.get("quantity")),
                    payload.get("description"),
                    payload.get("image_url"),
                    product_id,
                ),
            )
    finally:
        conn.close()


def insert_price_history(product_id: int, old_price: Decimal, new_price: Decimal) -> None:
    """Log a price change."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pricehistory (product_id, old_price, new_price, change_date)
                VALUES (%s, %s, %s, NOW())
                """,
                (product_id, old_price, new_price),
            )
    finally:
        conn.close()


def archive_product(product_id: int) -> None:
    """Mark a product as archived."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE product SET archived = 1, updated_at = NOW() WHERE product_id = %s",
                (product_id,),
            )
    finally:
        conn.close()


def _table_exists(cursor, table_name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s
        """,
        (DB_NAME, table_name),
    )
    row = cursor.fetchone()
    return bool(row and row.get("cnt"))


def product_has_open_orders(product_id: int) -> bool:
    """
    Check for open orders referencing a product.
    Falls back gracefully if order tables are absent.
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if not (_table_exists(cur, "orders") and _table_exists(cur, "order_items")):
                return False

            cur.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE oi.product_id = %s
                  AND COALESCE(o.status, 'open') NOT IN ('completed','closed','cancelled')
                """,
                (product_id,),
            )
            row = cur.fetchone()
            return bool(row and row.get("cnt"))
    except Exception:
        # If the schema differs, do not block the archive.
        return False
    finally:
        conn.close()


def search_products(filters: Dict, page: int, per_page: int = 10) -> Tuple[List[Dict], int]:
    """Search with filters + pagination."""
    where_clauses = ["archived = 0"]
    params: List = []

    if filters.get("sku"):
        where_clauses.append("SKU LIKE %s")
        params.append(f"%{filters['sku']}%")
    if filters.get("category"):
        where_clauses.append("category = %s")
        params.append(filters["category"])
    if filters.get("keyword"):
        where_clauses.append("(title LIKE %s OR description LIKE %s)")
        kw = f"%{filters['keyword']}%"
        params.extend([kw, kw])
    if filters.get("min_price") is not None:
        where_clauses.append("price >= %s")
        params.append(Decimal(filters["min_price"]))
    if filters.get("max_price") is not None:
        where_clauses.append("price <= %s")
        params.append(Decimal(filters["max_price"]))

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    offset = (page - 1) * per_page

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS total FROM product{where_sql}", params)
            total = cur.fetchone().get("total", 0)

            cur.execute(
                f"""
                SELECT * FROM product
                {where_sql}
                ORDER BY updated_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [per_page, offset],
            )
            rows = cur.fetchall()
            return rows, total
    finally:
        conn.close()


def inventory_value_by_category() -> List[Dict]:
    """Return SUM(price * quantity) grouped by category."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT category, SUM(price * quantity) AS total_value
                FROM product
                WHERE archived = 0
                GROUP BY category
                ORDER BY category
                """
            )
            return cur.fetchall()
    finally:
        conn.close()


def fetch_idle_stock(days: int) -> List[Dict]:
    """Return products idle more than X days."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    product_id, SKU, title, category, price, quantity,
                    DATEDIFF(NOW(), COALESCE(updated_at, created_at)) AS days_idle
                FROM product
                WHERE archived = 0
                  AND (updated_at IS NULL OR updated_at < NOW() - INTERVAL %s DAY)
                ORDER BY days_idle DESC, quantity DESC
                """,
                (days,),
            )
            return cur.fetchall()
    finally:
        conn.close()
