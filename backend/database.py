"""
Shared SQLite database for tracking player progress across all banks.
"""
import sqlite3
import os
import threading
import secrets
import time

DB_PATH = os.environ.get("DB_PATH", "/data/ctf.db")
_lock = threading.Lock()


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock:
        conn = get_conn()
        c = conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id   TEXT PRIMARY KEY,
            bank_id      INTEGER NOT NULL,
            player_ip    TEXT,
            created_at   REAL NOT NULL,
            authenticated INTEGER DEFAULT 0,
            balance_stolen REAL DEFAULT 0.0,
            tx_count     INTEGER DEFAULT 0,
            completed    INTEGER DEFAULT 0,
            token        TEXT,
            locked       INTEGER DEFAULT 0,
            last_rate_ts REAL DEFAULT 0.0,
            rate_bucket  INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS broker_attempts (
            attempt_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            player_ip    TEXT NOT NULL,
            attempt_ts   REAL NOT NULL,
            broker_session TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS broker_sessions (
            broker_session TEXT PRIMARY KEY,
            player_ip    TEXT NOT NULL,
            created_at   REAL NOT NULL,
            wrong_count  INTEGER DEFAULT 0,
            locked       INTEGER DEFAULT 0,
            tokens_submitted TEXT DEFAULT ''
        );
        """)
        conn.commit()
        conn.close()


# ── Session helpers ──────────────────────────────────────────────────────────

def create_session(bank_id: int, player_ip: str) -> str:
    sid = secrets.token_hex(16)
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT INTO sessions VALUES (?,?,?,?,0,0.0,0,0,NULL,0,0.0,0)",
            (sid, bank_id, player_ip, time.time())
        )
        conn.commit()
        conn.close()
    return sid


def get_session(session_id: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM sessions WHERE session_id=?", (session_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def authenticate_session(session_id: str):
    with _lock:
        conn = get_conn()
        conn.execute(
            "UPDATE sessions SET authenticated=1 WHERE session_id=?", (session_id,)
        )
        conn.commit()
        conn.close()


def record_theft(session_id: str, amount: float) -> dict:
    """Add amount to stolen balance. Returns updated session or None if locked/not-authed."""
    with _lock:
        conn = get_conn()
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id=?", (session_id,)
        ).fetchone()
        if not row:
            conn.close()
            return {"error": "session_not_found"}
        row = dict(row)

        if row["locked"]:
            conn.close()
            return {"error": "account_locked"}
        if not row["authenticated"]:
            conn.close()
            return {"error": "not_authenticated"}
        if row["completed"]:
            conn.close()
            return {"error": "already_completed"}

        # IDS rate-limit: max 200 req/s
        now = time.time()
        window = now - row["last_rate_ts"]
        bucket = row["rate_bucket"]
        if window < 1.0:
            bucket += 1
            if bucket > 200:
                conn.execute(
                    "UPDATE sessions SET locked=1 WHERE session_id=?", (session_id,)
                )
                conn.commit()
                conn.close()
                return {"error": "rate_limit_exceeded_account_locked"}
        else:
            bucket = 1

        new_balance = round(row["balance_stolen"] + amount, 2)
        new_tx = row["tx_count"] + 1
        token = row["token"]
        completed = row["completed"]

        if new_balance >= 1000.00 and not completed:
            token = f"TOKEN_{_bank_code(row['bank_id'])}_{secrets.token_hex(4).upper()}"
            completed = 1

        conn.execute(
            """UPDATE sessions SET
               balance_stolen=?, tx_count=?, completed=?, token=?,
               last_rate_ts=?, rate_bucket=?
               WHERE session_id=?""",
            (new_balance, new_tx, completed, token, now, bucket, session_id)
        )
        conn.commit()
        conn.close()
        return {
            "balance": new_balance,
            "tx_count": new_tx,
            "completed": bool(completed),
            "token": token
        }


def _bank_code(bank_id: int) -> str:
    codes = {1: "ALPHA", 2: "BETA", 3: "GAMMA", 4: "DELTA", 5: "EPSILON"}
    return codes.get(bank_id, "UNKNOWN")


def get_token(session_id: str) -> str | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT token, completed FROM sessions WHERE session_id=?", (session_id,)
    ).fetchone()
    conn.close()
    if row and row["completed"]:
        return row["token"]
    return None


# ── Broker helpers ────────────────────────────────────────────────────────────

def create_broker_session(player_ip: str) -> str:
    bsid = secrets.token_hex(12)
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT INTO broker_sessions VALUES (?,?,?,0,0,'')",
            (bsid, player_ip, time.time())
        )
        conn.commit()
        conn.close()
    return bsid


def get_broker_session(bsid: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM broker_sessions WHERE broker_session=?", (bsid,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def broker_wrong_attempt(bsid: str) -> dict:
    """Increment wrong count. Lock at 3. Returns updated session."""
    with _lock:
        conn = get_conn()
        row = conn.execute(
            "SELECT * FROM broker_sessions WHERE broker_session=?", (bsid,)
        ).fetchone()
        if not row:
            conn.close()
            return {"error": "not_found"}
        row = dict(row)
        if row["locked"]:
            conn.close()
            return {"locked": True, "wrong_count": row["wrong_count"]}
        new_wrong = row["wrong_count"] + 1
        locked = 1 if new_wrong >= 3 else 0
        conn.execute(
            "UPDATE broker_sessions SET wrong_count=?, locked=? WHERE broker_session=?",
            (new_wrong, locked, bsid)
        )
        conn.commit()
        conn.close()
        return {"locked": bool(locked), "wrong_count": new_wrong}


def broker_submit_token(bsid: str, token: str) -> dict:
    """
    Validate a token against any completed session.
    Returns {'valid': bool, 'bank_id': int} 
    """
    conn = get_conn()
    row = conn.execute(
        "SELECT bank_id FROM sessions WHERE token=? AND completed=1", (token,)
    ).fetchone()
    conn.close()
    if row:
        return {"valid": True, "bank_id": row["bank_id"]}
    return {"valid": False}


def broker_all_five_collected(bsid: str) -> bool:
    bs = get_broker_session(bsid)
    if not bs:
        return False
    submitted = [t.strip() for t in bs["tokens_submitted"].split(",") if t.strip()]
    # verify each token is valid and covers all 5 banks
    conn = get_conn()
    valid_banks = set()
    for tok in submitted:
        row = conn.execute(
            "SELECT bank_id FROM sessions WHERE token=? AND completed=1", (tok,)
        ).fetchone()
        if row:
            valid_banks.add(row["bank_id"])
    conn.close()
    return len(valid_banks) == 5


def broker_add_token(bsid: str, token: str):
    with _lock:
        conn = get_conn()
        row = conn.execute(
            "SELECT tokens_submitted FROM broker_sessions WHERE broker_session=?", (bsid,)
        ).fetchone()
        existing = row["tokens_submitted"] if row else ""
        tokens = [t.strip() for t in existing.split(",") if t.strip()]
        if token not in tokens:
            tokens.append(token)
        conn.execute(
            "UPDATE broker_sessions SET tokens_submitted=? WHERE broker_session=?",
            (",".join(tokens), bsid)
        )
        conn.commit()
        conn.close()
