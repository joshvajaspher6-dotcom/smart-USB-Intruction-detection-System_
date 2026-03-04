# db.py - Neon PostgreSQL database helper
import psycopg2
import psycopg2.extras
import time

# ─── Neon PostgreSQL Connection String ───────────────────────────────────────
DATABASE_URL = (
    "postgresql://neondb_owner:npg_I2PRZlWQ6Ktu"
    "@ep-tiny-sea-ai88kkrj-pooler.c-4.us-east-1.aws.neon.tech"
    "/neondb?sslmode=require&channel_binding=require"
)

# ─── Init (lazy — created on first use) ──────────────────────────────────────
_conn = None

def _get_conn():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(DATABASE_URL)
        _conn.autocommit = True
        print("✅ Neon PostgreSQL connected")
    return _conn


# ─── Simple Cache ─────────────────────────────────────────────────────────────
_cache     = {}
_cache_ttl = 3  # seconds

def _cached(key, fetch_fn):
    now = time.time()
    if key in _cache and (now - _cache[key]["time"]) < _cache_ttl:
        return _cache[key]["data"]
    data = fetch_fn()
    _cache[key] = {"data": data, "time": now}
    return data

def invalidate_cache():
    _cache.clear()


# ─── Init ─────────────────────────────────────────────────────────────────────
def initialize_database():
    """Connect and ensure table exists (uses existing table schema as-is)."""
    _get_conn()
    print("✅ Neon PostgreSQL ready")


# ─── Get ALL devices ──────────────────────────────────────────────────────────
def get_all_devices_full():
    """Returns everything the dashboard needs, deduplicated by VID:PID."""
    def _fetch():
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, usb_vid, usb_pid, usb_serial, device_type,
                       threat_level, last_seen
                FROM device_details
                ORDER BY last_seen DESC
            """)
            rows = cur.fetchall()

        grouped = {}
        for row in rows:
            d   = dict(row)
            key = f"{d['usb_vid']}:{d['usb_pid']}"
            if key not in grouped:
                grouped[key]                    = d
                grouped[key]["interface_count"] = 1
                grouped[key]["all_serials"]     = d.get("usb_serial", "") or ""
            else:
                grouped[key]["interface_count"] += 1
                existing = grouped[key]["all_serials"]
                serial   = d.get("usb_serial", "") or ""
                if serial and serial not in existing.split(","):
                    grouped[key]["all_serials"] = f"{existing},{serial}"

        return list(grouped.values())

    return _cached("all_devices", _fetch)


# ─── Single-row lookups ───────────────────────────────────────────────────────
def get_device_by_id(device_id):
    """Fetch a single device by its integer ID."""
    conn = _get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM device_details WHERE id = %s", (device_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def get_device_by_vid_pid(vid, pid):
    """Fetch the most recently seen device matching VID and PID."""
    conn = _get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * FROM device_details
            WHERE usb_vid = %s AND usb_pid = %s
            ORDER BY last_seen DESC
            LIMIT 1
            """,
            (vid, pid)
        )
        row = cur.fetchone()
    return dict(row) if row else None


def count_interfaces(vid, pid):
    """Count distinct serials for a given VID+PID."""
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(DISTINCT usb_serial) FROM device_details WHERE usb_vid = %s AND usb_pid = %s",
            (vid, pid)
        )
        result = cur.fetchone()
    return result[0] if result else 0


def get_device_types(vid, pid):
    """Return list of device_type values for all records matching VID+PID."""
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT device_type FROM device_details WHERE usb_vid = %s AND usb_pid = %s",
            (vid, pid)
        )
        rows = cur.fetchall()
    return [r[0] for r in rows]


# ─── Insert / Update / Delete ─────────────────────────────────────────────────
def insert_device(vid, pid, serial):
    """
    Insert a new device or update last_seen if it already exists (matched by vid+pid+serial).
    Returns the integer row ID.
    """
    conn = _get_conn()
    with conn.cursor() as cur:
        # Check if this exact device already exists
        cur.execute(
            "SELECT id FROM device_details WHERE usb_vid = %s AND usb_pid = %s AND usb_serial = %s",
            (vid, pid, serial)
        )
        row = cur.fetchone()

        if row:
            # Already exists — just touch last_seen
            cur.execute(
                "UPDATE device_details SET last_seen = EXTRACT(EPOCH FROM NOW())::real WHERE id = %s",
                (row[0],)
            )
            invalidate_cache()
            return row[0]
        else:
            # New device — insert and return the auto-generated id
            cur.execute(
                """
                INSERT INTO device_details (usb_vid, usb_pid, usb_serial,
                                            device_type, threat_level, last_seen)
                VALUES (%s, %s, %s, 'unknown', 'unknown', EXTRACT(EPOCH FROM NOW())::real)
                RETURNING id
                """,
                (vid, pid, serial)
            )
            new_id = cur.fetchone()[0]
            invalidate_cache()
            return new_id


def update_device_status(vid, pid, device_type, threat_level):
    """Update device_type and threat_level for all records matching VID+PID."""
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE device_details
            SET device_type = %s, threat_level = %s,
                last_seen = EXTRACT(EPOCH FROM NOW())::real
            WHERE usb_vid = %s AND usb_pid = %s
            """,
            (device_type, threat_level, vid, pid)
        )
        count = cur.rowcount
    invalidate_cache()
    return count


def update_device_serial(device_id, serial_csv):
    """Update the usb_serial field for a specific integer row ID."""
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE device_details
            SET usb_serial = %s, last_seen = EXTRACT(EPOCH FROM NOW())::real
            WHERE id = %s
            """,
            (serial_csv, device_id)
        )
    invalidate_cache()


def delete_device(vid, pid):
    """Delete all records matching VID+PID. Returns count of deleted rows."""
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM device_details WHERE usb_vid = %s AND usb_pid = %s",
            (vid, pid)
        )
        count = cur.rowcount
    invalidate_cache()
    return count