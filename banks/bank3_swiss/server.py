#!/usr/bin/env python3
"""
Bank 3 — Swiss Vault AG
Exploit: Currency Loop — USD→EUR→USD with truncation creates $0.01 discrepancy
Auth: Anti-debug binary; password hidden in .rsrc section
Side-Channel: No error messages — player must time response latency
Port: 9003
"""
import sys, socket, threading, time, random
sys.path.insert(0, "/app/backend")
from database import init_db, create_session, authenticate_session, record_theft, get_token
from passwords import bank3_password

BANK_ID = 3
PORT = 9003
RATE_USD_EUR = 0.9231   # Truncated, not rounded
RATE_EUR_USD = 1.0832

BANNER = r"""
╔══════════════════════════════════════════════════════╗
║           SWISS VAULT AG — PRIVATE TERMINAL          ║
║        "Discretion is our most valued asset."        ║
╚══════════════════════════════════════════════════════╝
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

def currency_loop_steal(amount_usd: float) -> float:
    """
    USD → EUR (truncate to 4 decimals) → USD (truncate to 4 decimals)
    The truncation creates a ~$0.01 gap exploitable by sending specific amounts.
    """
    eur = int(amount_usd * RATE_USD_EUR * 10000) / 10000  # truncate
    back_usd = int(eur * RATE_EUR_USD * 10000) / 10000    # truncate
    discrepancy = round(amount_usd - back_usd, 4)
    return discrepancy

def handle_client(conn, addr):
    ip = addr[0]
    send(conn, BANNER)
    send(conn, "[*] Binary: auth_node_3.elf — WARNING: Contains anti-debugging countermeasures.")
    send(conn, "[*] Password is embedded in the .rsrc section. Avoid breakpoints.\n")
    send(conn, "Password: ")

    attempt = recv_line(conn)
    correct = bank3_password()

    # Side-channel: correct password has slightly shorter sleep
    if attempt == correct:
        time.sleep(0.05 + random.uniform(0, 0.01))   # fast path (~50ms)
        sid = create_session(BANK_ID, ip)
        authenticate_session(sid)
        send(conn, "\n[+] VAULT OPENED.")
        send(conn, f"[*] Session: {sid}")
        send(conn, "[*] Exploit: Currency Loop — send amount that loses $0.01 in USD→EUR→USD conversion.")
        send(conn, "[*] Note: This vault gives NO error messages. Time the response to detect success.\n")
    else:
        time.sleep(0.15 + random.uniform(0, 0.05))   # slow path (~150-200ms — side channel)
        # Swiss Vault: NO error message
        conn.close()
        return

    while True:
        send(conn, "swiss> ")
        cmd = recv_line(conn).strip()
        if not cmd:
            continue

        if cmd.lower() == "help":
            send(conn, "Commands: transfer <amount> | status | token | exit")

        elif cmd.lower().startswith("transfer "):
            try:
                raw = float(cmd.split()[1])
            except (IndexError, ValueError):
                # Side channel: no error msg on bad parse either
                continue

            discrepancy = currency_loop_steal(raw)
            t_start = time.time()

            if discrepancy >= 0.0099:
                stolen = 0.01
                result = record_theft(sid, stolen)
                elapsed = time.time() - t_start
                if "error" in result:
                    # Side channel ONLY: fast vs slow response
                    time.sleep(0.02)  # fast = error
                else:
                    time.sleep(0.08)  # slow = success (side channel tell)
                    send(conn, f".")   # Swiss vault: just a dot for success
                    if result["completed"]:
                        send(conn, f"\n[!!!] VAULT EMPTIED — $1,000.00")
                        send(conn, f"[*]  Token: {result['token']}")
                        break
            else:
                time.sleep(0.02)  # fast = no exploit (side channel)

        elif cmd.lower() == "status":
            from database import get_session
            s = get_session(sid)
            if s:
                send(conn, f"[*] Stolen: ${s['balance_stolen']:.2f} | Tx: {s['tx_count']}")

        elif cmd.lower() == "token":
            tok = get_token(sid)
            send(conn, f"[*] Token: {tok}" if tok else "[-] Not yet.")

        elif cmd.lower() in ("exit", "quit"):
            break

    conn.close()


def main():
    init_db()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(50)
    print(f"[Bank3-Swiss] Listening on 0.0.0.0:{PORT}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
