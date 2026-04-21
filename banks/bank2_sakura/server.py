#!/usr/bin/env python3
"""
Bank 2 — Sakura Financial Group
Exploit: IEEE 754 Precision — high-precision double loses value on float32 cast
Auth: HMAC-SHA1 of 60-second epoch window (reverse-engineer binary for the logic)
Port: 9002
"""
import sys, socket, threading, struct, time
sys.path.insert(0, "/app/backend")
from database import init_db, create_session, authenticate_session, record_theft, get_token
from passwords import bank2_password, bank2_time_remaining

BANK_ID = 2
PORT = 9002
BANNER = r"""
╔══════════════════════════════════════════════════════╗
║        SAKURA FINANCIAL GROUP — SECURE TERMINAL      ║
║           "桜の精神で守られた資産"                      ║
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

def ieee754_exploit(value: float) -> float:
    """
    Simulate server casting double -> float32 -> double.
    A value like 1.0000001192092896 becomes 1.0 after float32 cast.
    The difference is credited to the player's siphon account.
    """
    as_float32 = struct.unpack('f', struct.pack('f', value))[0]
    return round(value - as_float32, 10)

def handle_client(conn, addr):
    ip = addr[0]
    send(conn, BANNER)
    remaining = bank2_time_remaining()
    send(conn, f"[*] Download the authentication binary: auth_node_2.elf")
    send(conn, f"[*] Password rotates every 60 seconds. Current window expires in {remaining}s")
    send(conn, "[*] Reverse-engineer the HMAC derivation logic from the binary.\n")
    send(conn, "Password: ")

    attempt = recv_line(conn)
    correct = bank2_password()
    if attempt != correct:
        send(conn, "\n[-] ACCESS DENIED. Password mismatch (or window expired).")
        conn.close()
        return

    sid = create_session(BANK_ID, ip)
    authenticate_session(sid)
    send(conn, "\n[+] ACCESS GRANTED.")
    send(conn, f"[*] Session: {sid}")
    send(conn, "[*] Exploit: IEEE 754 — send a double that loses $0.01 when cast to float32.")
    send(conn, "[*] Hint: 1.0099999904632568 as float32 = 1.00999999...")
    send(conn, "[*] Magic value: 0.010000001192092896\n")

    while True:
        send(conn, "sakura> ")
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

            # Server casts double to float32 — precision is lost
            discrepancy = ieee754_exploit(raw)
            if discrepancy >= 0.009999:
                stolen = 0.01
                result = record_theft(sid, stolen)
                if "error" in result:
                    send(conn, f"[-] {result['error']}")
                    if "locked" in result["error"]:
                        send(conn, "[-] IDS ALERT — Account locked."); break
                else:
                    send(conn, f"[+] Siphoned: ${stolen:.2f} | Total: ${result['balance']:.2f} | Tx #{result['tx_count']}")
                    if result["completed"]:
                        send(conn, f"\n[!!!] $1,000.00 SIPHONED COMPLETE")
                        send(conn, f"[*]  Token: {result['token']}")
                        break
            else:
                send(conn, f"[-] Transfer of ${raw:.15f} processed normally. No exploit detected.")

        elif cmd.lower() == "balance":
            from database import get_session
            s = get_session(sid)
            if s:
                send(conn, f"[*] Stolen: ${s['balance_stolen']:.2f} | Tx: {s['tx_count']}")

        elif cmd.lower() == "token":
            tok = get_token(sid)
            send(conn, f"[*] Token: {tok}" if tok else "[-] Not earned yet.")

        elif cmd.lower() in ("exit", "quit"):
            send(conn, "[*] Disconnecting."); break
        else:
            send(conn, "[-] Unknown command.")

    conn.close()


def main():
    init_db()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(50)
    print(f"[Bank2-Sakura] Listening on 0.0.0.0:{PORT}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
