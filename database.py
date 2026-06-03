"""Шар БД на aiosqlite: улюблене місто користувача + підписки на розсилку.

Дві таблиці:
  users         — улюблене місто (для «Моя погода») та останнє показане місто
                  (контекст для кнопок «Зробити улюбленим» / «Підписатися»);
  subscriptions — щоденна розсилка о певній годині (час київський, HH:MM).
"""

import logging
import os

import aiosqlite

from config import DB_PATH

logger = logging.getLogger(__name__)

_db: aiosqlite.Connection | None = None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    fav_city   TEXT,
    fav_lat    REAL,
    fav_lon    REAL,
    last_city  TEXT,
    last_lat   REAL,
    last_lon   REAL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS subscriptions (
    user_id    INTEGER PRIMARY KEY,
    city       TEXT NOT NULL,
    lat        REAL NOT NULL,
    lon        REAL NOT NULL,
    send_time  TEXT NOT NULL,
    is_active  INTEGER NOT NULL DEFAULT 1
);
"""


async def init_db() -> None:
    global _db
    # SQLite не створює відсутніх тек — створюємо батьківську теку самі
    # (важливо для шляхів типу /data/weather.db на хостингу з томом).
    parent = os.path.dirname(DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    _db = await aiosqlite.connect(DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.executescript(_SCHEMA)
    await _db.commit()
    await _migrate()


async def _migrate() -> None:
    """Доганяє схему для вже створених БД: додає нові колонки users, якщо їх нема."""
    cur = await _conn().execute("PRAGMA table_info(users)")
    cols = {row["name"] for row in await cur.fetchall()}
    for col, decl in (("last_city", "TEXT"), ("last_lat", "REAL"), ("last_lon", "REAL")):
        if col not in cols:
            await _conn().execute(f"ALTER TABLE users ADD COLUMN {col} {decl}")
    await _conn().commit()


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None


def _conn() -> aiosqlite.Connection:
    if _db is None:
        raise RuntimeError("База даних не ініціалізована (виклич init_db).")
    return _db


# ── Улюблене місто ────────────────────────────────────────────────────────────

async def set_favorite(user_id: int, city: str, lat: float, lon: float) -> None:
    await _conn().execute(
        """
        INSERT INTO users (user_id, fav_city, fav_lat, fav_lon)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            fav_city = excluded.fav_city,
            fav_lat  = excluded.fav_lat,
            fav_lon  = excluded.fav_lon
        """,
        (user_id, city, lat, lon),
    )
    await _conn().commit()


async def get_favorite(user_id: int) -> dict | None:
    cur = await _conn().execute(
        "SELECT fav_city, fav_lat, fav_lon FROM users WHERE user_id = ?",
        (user_id,),
    )
    row = await cur.fetchone()
    if row is None or row["fav_city"] is None:
        return None
    return {"city": row["fav_city"], "lat": row["fav_lat"], "lon": row["fav_lon"]}


# ── Останнє показане місто ────────────────────────────────────────────────────
# Контекст для інлайн-кнопок під карткою (назва міста не вміщується в 64 байти
# callback_data, тож тримаємо останній показ у БД — переживає рестарт бота).

async def set_last_seen(user_id: int, city: str, lat: float, lon: float) -> None:
    await _conn().execute(
        """
        INSERT INTO users (user_id, last_city, last_lat, last_lon)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            last_city = excluded.last_city,
            last_lat  = excluded.last_lat,
            last_lon  = excluded.last_lon
        """,
        (user_id, city, lat, lon),
    )
    await _conn().commit()


async def get_last_seen(user_id: int) -> dict | None:
    cur = await _conn().execute(
        "SELECT last_city, last_lat, last_lon FROM users WHERE user_id = ?",
        (user_id,),
    )
    row = await cur.fetchone()
    if row is None or row["last_city"] is None:
        return None
    return {"city": row["last_city"], "lat": row["last_lat"], "lon": row["last_lon"]}


# ── Підписки ──────────────────────────────────────────────────────────────────

async def upsert_subscription(
    user_id: int, city: str, lat: float, lon: float, send_time: str
) -> None:
    await _conn().execute(
        """
        INSERT INTO subscriptions (user_id, city, lat, lon, send_time, is_active)
        VALUES (?, ?, ?, ?, ?, 1)
        ON CONFLICT(user_id) DO UPDATE SET
            city      = excluded.city,
            lat       = excluded.lat,
            lon       = excluded.lon,
            send_time = excluded.send_time,
            is_active = 1
        """,
        (user_id, city, lat, lon, send_time),
    )
    await _conn().commit()


async def disable_subscription(user_id: int) -> bool:
    """Вимикає підписку. Повертає True, якщо була активна."""
    cur = await _conn().execute(
        "UPDATE subscriptions SET is_active = 0 WHERE user_id = ? AND is_active = 1",
        (user_id,),
    )
    await _conn().commit()
    return cur.rowcount > 0


async def get_subscription(user_id: int) -> dict | None:
    cur = await _conn().execute(
        """
        SELECT city, lat, lon, send_time, is_active
        FROM subscriptions WHERE user_id = ?
        """,
        (user_id,),
    )
    row = await cur.fetchone()
    if row is None:
        return None
    return dict(row)


async def due_subscriptions(hhmm: str) -> list[dict]:
    """Активні підписки, час яких збігається з поточним HH:MM (київський)."""
    cur = await _conn().execute(
        """
        SELECT user_id, city, lat, lon, send_time
        FROM subscriptions
        WHERE is_active = 1 AND send_time = ?
        """,
        (hhmm,),
    )
    rows = await cur.fetchall()
    return [dict(r) for r in rows]
