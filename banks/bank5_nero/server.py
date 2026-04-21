#!/usr/bin/env python3
"""
Bank 5 — Nero Digital
Exploit: Banker's Rounding v2 — forced .5 rounds to nearest even (down), stealing $0.01
Auth: Proof-of-Work — solve sha256(nonce + CHALLENGE)[:5] == "00000" first, then authenticate
Port: 9005
"""
import sys, socket, threading, hashlib
sys.path.insert(0, "/app/backend")
from database import init_db, create_session, authenticate_session, record_theft, get_token
from passwords import bank5_challenge, bank5_verify_pow, bank5_password

BANK_ID = 5
PORT = 9005
BANNER = r"""
╔══════════════════════════════════════════════════════╗
║          NERO DIGITAL BANK — QUANTUM VAULT           ║
║       "The future of money, secured by math."        ║
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

def banker_round_v2(amount: float) -> float:
    """
    Server rounds all amounts to 2 decimal places using Banker's Rounding.
    Sending 0.005 rounds to 0.00 (nearest even), but the POSTED amount is 0.01.
    Discrepancy = 0.01.
    """
    from decimal import Decimal, ROUND_HALF_EVEN
    d = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
    return float(d)

def handle_client(conn, addr):
    ip = addr[0]
    send(conn, BANNER)
    send(conn, "[*] Binary: auth_node_5.elf")
    send(conn, "[*] ANTI-BOT GATE: Solve a Proof-of-Work challenge first.\n")

    # PoW gate
    challenge = bank5_challenge()
    send(conn, f"[PoW] Find nonce N such that SHA256(N + '{challenge}') starts with '00000'")
    send(conn, f"[PoW] Challenge: {challenge}")
    send(conn, "Nonce: ")

    nonce = recv_line(conn)
    if not bank5_verify_pow(nonce):
        send(conn, "[-] PoW FAILED. Invalid nonce.")
        conn.close()
        return

    send(conn, "[+] PoW Accepted.")
    derived_pw = bank5_password(nonce)
    send(conn, f"[*] Your session password: {derived_pw}")
    send(conn, "\nPassword (re-enter derived password to authenticate): ")

    attempt = recv_line(conn)
    if attempt != derived_pw:
        send(conn, "[-] Authentication failed.")
        conn.close()
        return

    sid = create_session(BANK_ID, ip)
    authenticate_session(sid)
    send(conn, "\n[+] NERO DIGITAL VAULT UNLOCKED.")
    send(conn, f"[*] Session: {sid}")
    send(conn, "[*] Exploit: Banker's Rounding — 0.005 rounds DOWN to 0.00,")
    send(conn, "[*]          but the posted debit shows $0.01. Discrepancy = $0.01.")
    send(conn, "[*] Magic amount: 0.005\n")

    while True:
        send(conn, "nero> ")
        cmd = recv_line(conn).strip()
        if not cmd:
            continue

        if cmd.lower() == "help":
            send(conn, "Commands: transfer <amount> | balance | token | exit")

        elif cmd.lower().startswith("transfer "):
            try:
                raw = float(cmd.split()[1])
            except (IndexError, ValueError):
                send(conn, "[-] Usage: transfer <amount>")
                continue

            rounded = banker_round_v2(raw)
            if abs(raw - 0.005) < 1e-9:
                # 0.005 rounds to 0.00 (Banker's: nearest even = 0)
                # But ledger charges 0.01 minimum → discrepancy = 0.01
                stolen = 0.01
                result = record_theft(sid, stolen)
                if "error" in result:
                    send(conn, f"[-] {result['error']}")
                    if "locked" in result["error"]: break
                else:
                    send(conn, f"[+] Rounding discrepancy: ${stolen:.2f} siphoned | Total: ${result['balance']:.2f} | Tx #{result['tx_count']}")
                    if result["completed"]:
                        send(conn, f"\n[!!!] QUANTUM VAULT DRAINED — $1,000.00")
                        send(conn, f"[*]  Token: {result['token']}")
                        break
            else:
                send(conn, f"[-] Transfer ${raw:.6f} → rounded to ${rounded:.2f}. No exploit.")

        elif cmd.lower() == "balance":
            from database import get_session
            s = get_session(sid)
            if s:
                send(conn, f"[*] Stolen: ${s['balance_stolen']:.2f} | Tx: {s['tx_count']}")

        elif cmd.lower() == "token":
            tok = get_token(sid)
            send(conn, f"[*] Token: {tok}" if tok else "[-] Not yet.")

        elif cmd.lower() in ("exit", "quit"):
            break
        else:
            send(conn, "[-] Unknown command.")

    conn.close()


def main():
    init_db()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(50)
    print(f"[Bank5-Nero] Listening on 0.0.0.0:{PORT}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
