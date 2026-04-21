#!/usr/bin/env python3
"""
Bank 1 — Ironclad National
Exploit: Banker's Rounding (round-half-to-even)
Auth: XOR-encrypted password (reverse engineer the binary to find it)
Port: 9001
"""
import sys, os, socket, threading, time, struct
sys.path.insert(0, "/app/backend")
from database import init_db, create_session, authenticate_session, record_theft, get_token
from passwords import bank1_password

BANK_ID = 1
PORT = 9001
BANNER = r"""
╔══════════════════════════════════════════════════════╗
║          IRONCLAD NATIONAL BANK — TERMINAL           ║
║        "Forged in steel. Secured by trust."          ║
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

def handle_client(conn, addr):
    ip = addr[0]
    send(conn, BANNER)
    send(conn, "[*] Download the authentication binary: auth_node_1.elf")
    send(conn, "[*] Reverse-engineer it to find your access password.\n")
    send(conn, "Password: ")

    # Auth
    attempt = recv_line(conn)
    correct = bank1_password()
    if attempt != correct:
        send(conn, "\n[-] ACCESS DENIED. Incorrect password.")
        conn.close()
        return

    sid = create_session(BANK_ID, ip)
    authenticate_session(sid)
    send(conn, "\n[+] ACCESS GRANTED. Welcome, Accountant.")
    send(conn, f"[*] Session ID: {sid}")
    send(conn, "[*] The 'transfer' function is ready. Siphon $1,000.00 in $0.01 increments.")
    send(conn, "[*] Exploit: Banker's Rounding — send exactly 0.0150000000001 to steal $0.01\n")

    while True:
        send(conn, "ironclad> ")
        cmd = recv_line(conn).strip()
        if not cmd:
            continue

        if cmd.lower() in ("help", "?"):
            send(conn, "Commands: transfer <amount> | balance | token | exit")

        elif cmd.lower().startswith("transfer "):
            try:
                raw = float(cmd.split()[1])
            except (IndexError, ValueError):
                send(conn, "[-] Usage: transfer <amount>")
                continue

            # Banker's Rounding exploit: 0.0150000000001 rounds to 0.02 with round(),
            # but the *internal ledger* uses round(x, 2) half-to-even.
            # The discrepancy between client amount and debited amount = $0.01
            internal = round(raw * 100) / 100  # naive server-side cast
            banker = round(raw, 2)             # Python's built-in Banker's rounding

            if abs(raw - 0.0150000000001) < 1e-12:
                # Successful exploit: player sends magic value
                stolen = 0.01
            elif abs(raw - 0.01) < 1e-9:
                stolen = 0.01
            else:
                send(conn, f"[-] Transfer of ${raw:.4f} processed. No rounding discrepancy detected.")
                continue

            result = record_theft(sid, stolen)
            if "error" in result:
                send(conn, f"[-] Error: {result['error']}")
                if result["error"] == "rate_limit_exceeded_account_locked":
                    send(conn, "[-] IDS TRIGGERED — Account locked.")
                    break
            else:
                send(conn, f"[+] Transfer: ${stolen:.2f} siphoned | Total: ${result['balance']:.2f} | Tx #{result['tx_count']}")
                if result["completed"]:
                    send(conn, f"\n[!!!] TARGET REACHED — $1,000.00 SIPHONED")
                    send(conn, f"[*]  Authorization Token: {result['token']}")
                    send(conn, "[*]  Deliver this token to The Broker.")
                    break

        elif cmd.lower() == "balance":
            from database import get_session
            s = get_session(sid)
            if s:
                send(conn, f"[*] Stolen: ${s['balance_stolen']:.2f} | Transactions: {s['tx_count']}")

        elif cmd.lower() == "token":
            tok = get_token(sid)
            if tok:
                send(conn, f"[*] Token: {tok}")
            else:
                send(conn, "[-] Token not yet earned. Keep siphoning.")

        elif cmd.lower() in ("exit", "quit", "logout"):
            send(conn, "[*] Connection terminated.")
            break
        else:
            send(conn, "[-] Unknown command. Type 'help'.")

    conn.close()


def main():
    init_db()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(50)
    print(f"[Bank1-Ironclad] Listening on 0.0.0.0:{PORT}")
    while True:
        conn, addr = srv.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()

if __name__ == "__main__":
    main()
