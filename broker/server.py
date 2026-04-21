#!/usr/bin/env python3
"""
The Broker — Final Flag Exchange
Rules:
  - Player must submit all 5 tokens (one per bank)
  - 3 wrong token attempts → session locked, all bank sessions invalidated, passwords rotate
  - Flag released only when all 5 valid tokens covering all 5 banks are submitted
Port: 9999
"""
import sys, socket, threading, time
sys.path.insert(0, "/app/backend")
from database import (
    init_db, create_broker_session, get_broker_session,
    broker_wrong_attempt, broker_submit_token,
    broker_add_token, broker_all_five_collected,
    get_conn
)

PORT = 9999

# ── Encrypted flag ───────────────────────────────────────────────────────────
# The plaintext flag is: ronin{0n3_C3nt_5_B4nk5_0n3_M45t3rm1nd_92}
# Encrypted with AES-128-CBC. Players must decrypt it to claim the flag.
#
# Algorithm : AES-128-CBC
# Key       : OneCentThiefKey!   (16 bytes — hidden across the 5 bank binaries)
# IV        : SalamiSliceIV!!!   (16 bytes — hinted by the challenge theme)
# Ciphertext: base64-encoded below
#
# Key hint: each bank binary leaks one segment of the key when solved:
#   Bank1 → "OneC"   Bank2 → "entT"   Bank3 → "hief"   Bank4 → "Key!"  (IV from Bank5)
ENCRYPTED_FLAG = "8TeTSXbc7AAYIOkU+fAWIB+iG4tJ4Q2xKrEe3zFBYPljupi9DPPj13N8mP+8wqhz"
ENCRYPTED_IV   = "U2FsYW1pU2xpY2VJViEhIQ=="  # base64("SalamiSliceIV!!!")
# ─────────────────────────────────────────────────────────────────────────────

BANNER = r"""
╔══════════════════════════════════════════════════════════════════╗
║                    T H E   B R O K E R                          ║
║            "Five banks. Five tokens. One payday."               ║
║                                                                  ║
║   You've siphoned the funds. Now collect your reward.           ║
║   Submit all 5 Authorization Tokens to receive the flag.        ║
║                                                                  ║
║   ⚠ WARNING: 3 invalid attempts will terminate this session.   ║
║              All bank passwords will rotate. Start over.        ║
╚══════════════════════════════════════════════════════════════════╝
"""

def send(conn, msg):
    conn.sendall((msg + "\n").encode())

def recv_line(conn) -> str:
    buf = b""
    while True:
        c = conn.recv(1)
        if not c or c == b"\n":
            return buf.decode(errors="replace").strip()
        buf += c

def invalidate_all_sessions():
    """Lock all authenticated sessions — forces players to start over."""
    with __import__('database', fromlist=['_lock'])._lock:
        conn = get_conn()
        conn.execute("UPDATE sessions SET locked=1, authenticated=0")
        conn.commit()
        conn.close()

def get_submitted_tokens(bsid: str) -> list:
    bs = get_broker_session(bsid)
    if not bs:
        return []
    return [t.strip() for t in bs["tokens_submitted"].split(",") if t.strip()]

def get_collected_banks(bsid: str) -> set:
    tokens = get_submitted_tokens(bsid)
    conn = get_conn()
    banks = set()
    for tok in tokens:
        row = conn.execute(
            "SELECT bank_id FROM sessions WHERE token=? AND completed=1", (tok,)
        ).fetchone()
        if row:
            banks.add(row["bank_id"])
    conn.close()
    return banks

BANK_NAMES = {1: "Ironclad", 2: "Sakura", 3: "Swiss Vault", 4: "Desert Gold", 5: "Nero Digital"}

def handle_client(conn, addr):
    ip = addr[0]
    send(conn, BANNER)
    send(conn, f"[*] Connection from {ip}")

    bsid = create_broker_session(ip)
    send(conn, f"[*] Broker Session: {bsid}\n")

    while True:
        bs = get_broker_session(bsid)
        if bs and bs["locked"]:
            send(conn, "\n[!!!] SESSION TERMINATED — 3 WRONG ATTEMPTS")
            send(conn, "[!!!] All bank sessions have been invalidated.")
            send(conn, "[!!!] All passwords have rotated. You must re-infiltrate all banks.")
            send(conn, "[!!!] The Accountant's trail has gone cold.\n")
            invalidate_all_sessions()
            conn.close()
            return

        collected = get_collected_banks(bsid)
        remaining = set(range(1, 6)) - collected

        if collected:
            send(conn, f"[*] Tokens collected: {len(collected)}/5 — Banks: {', '.join(BANK_NAMES[b] for b in sorted(collected))}")
        if remaining:
            send(conn, f"[*] Still needed: {', '.join(BANK_NAMES[b] for b in sorted(remaining))}")

        send(conn, "\nbroker> submit <TOKEN> | status | exit")
        send(conn, "broker> ")
        cmd = recv_line(conn).strip()

        if not cmd:
            continue

        if cmd.lower() == "exit":
            send(conn, "[*] Come back when you have all 5 tokens.")
            break

        elif cmd.lower() == "status":
            wrong = bs["wrong_count"] if bs else 0
            send(conn, f"[*] Tokens: {len(collected)}/5 | Wrong attempts: {wrong}/3")
            if collected:
                for b in sorted(collected):
                    send(conn, f"    ✓ Bank {b} ({BANK_NAMES[b]})")
            for b in sorted(remaining):
                send(conn, f"    ✗ Bank {b} ({BANK_NAMES[b]})")

        elif cmd.lower().startswith("submit "):
            token = cmd.split(" ", 1)[1].strip()

            # Check if already submitted
            if token in get_submitted_tokens(bsid):
                send(conn, f"[*] Token already submitted and accepted.")
                continue

            result = broker_submit_token(bsid, token)

            if result["valid"]:
                bank_id = result["bank_id"]
                if bank_id in collected:
                    send(conn, f"[*] You already have a token for Bank {bank_id} ({BANK_NAMES[bank_id]}).")
                    continue
                broker_add_token(bsid, token)
                send(conn, f"\n[+] TOKEN ACCEPTED — Bank {bank_id} ({BANK_NAMES[bank_id]}) verified.")
                send(conn, f"[+] Progress: {len(collected)+1}/5 tokens")

                # Check for all 5
                if broker_all_five_collected(bsid):
                    send(conn, "\n" + "═" * 66)
                    send(conn, "  [!!!] ALL FIVE TOKENS VERIFIED. THE HEIST IS COMPLETE.")
                    send(conn, "═" * 66)
                    send(conn, "")
                    send(conn, "  The Broker leans back, lights a cigarette, and slides")
                    send(conn, "  an envelope across the table.")
                    send(conn, "")
                    send(conn, "  'You earned it, Accountant. But I don't hand out")
                    send(conn, "   plaintext. That's not how this business works.'")
                    send(conn, "")
                    send(conn, "  'Decrypt this first.'")
                    send(conn, "")
                    send(conn, "─" * 66)
                    send(conn, "  [ENCRYPTED REWARD]")
                    send(conn, "")
                    send(conn, f"  Algorithm  : AES-128-CBC")
                    send(conn, f"  IV (base64): {ENCRYPTED_IV}")
                    send(conn, f"  Ciphertext : {ENCRYPTED_FLAG}")
                    send(conn, "")
                    send(conn, "  Hint: The key is 16 characters. You've seen fragments")
                    send(conn, "  of it across all five banks. Assemble the pieces.")
                    send(conn, "─" * 66)
                    send(conn, "")
                    send(conn, "  python3 -c \"")
                    send(conn, "    from Crypto.Cipher import AES")
                    send(conn, "    from Crypto.Util.Padding import unpad")
                    send(conn, "    import base64")
                    send(conn, "    key = b'????????????????'  # 16-char key")
                    send(conn, f"    iv  = base64.b64decode('{ENCRYPTED_IV}')")
                    send(conn, f"    ct  = base64.b64decode('{ENCRYPTED_FLAG}')")
                    send(conn, "    print(unpad(AES.new(key,AES.MODE_CBC,iv).decrypt(ct),16))")
                    send(conn, "  \"")
                    send(conn, "")
                    send(conn, "═" * 66)
                    conn.close()
                    return
            else:
                # Wrong token — increment counter
                updated = broker_wrong_attempt(bsid)
                wrong_count = updated["wrong_count"]
                attempts_left = 3 - wrong_count
                send(conn, f"\n[-] INVALID TOKEN — Token not recognized or bank not completed.")
                if attempts_left > 0:
                    send(conn, f"[-] WARNING: {attempts_left} attempt(s) remaining before session lockout.")
                else:
                    send(conn, "\n[!!!] FINAL ATTEMPT FAILED. SESSION TERMINATING...")
                    # Next loop iteration will trigger the lockout block

        else:
            send(conn, "[-] Unknown command. Use: submit <TOKEN> | status | exit")

    conn.close()


def main():
    init_db()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(50)
    print(f"[Broker] Listening on 0.0.0.0:{PORT}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
