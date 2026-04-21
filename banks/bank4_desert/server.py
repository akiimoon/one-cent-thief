#!/usr/bin/env python3
"""
Bank 4 — Desert Gold Exchange
Exploit: Integer Overflow — send large value that wraps a 32-bit int, leaving remainder of 1 cent
Auth: Custom VM binary — reverse the bytecode interpreter to derive password
Port: 9004
"""
import sys, socket, threading, ctypes
sys.path.insert(0, "/app/backend")
from database import init_db, create_session, authenticate_session, record_theft, get_token
from passwords import bank4_password

BANK_ID = 4
PORT = 9004
BANNER = r"""
╔══════════════════════════════════════════════════════╗
║         DESERT GOLD EXCHANGE — SECURE ACCESS         ║
║           "Where every grain of gold counts."        ║
╚══════════════════════════════════════════════════════╝
"""

# INT32_MAX = 2147483647
INT32_MAX = 0x7FFFFFFF
INT32_MOD  = 0x100000000   # 2^32

def send(conn, msg):
    conn.sendall((msg + "\n").encode())

def recv_line(conn) -> str:
    buf = b""
    while True:
        c = conn.recv(1)
        if not c or c == b"\n":
            return buf.decode(errors="replace").strip()
        buf += c

def integer_wrap_exploit(amount_cents: int) -> int:
    """
    Server stores balance as signed int32 (cents).
    Sending a value such that (balance + amount) overflows int32 and wraps to a small positive:
    We want (0 + amount) % INT32_MOD to result in 1 (1 cent).
    amount = INT32_MOD - current_balance + 1
    But simplest: the MAGIC amount is INT32_MAX + 2 = 2147483649
    which overflows to: 2147483649 % 4294967296 = 2147483649 → signed = -2147483647
    The server's abs() of remainder = 1 cent credited.
    """
    signed = ctypes.c_int32(amount_cents % INT32_MOD).value
    return abs(signed) % 100  # remainder in cents after overflow

def handle_client(conn, addr):
    ip = addr[0]
    send(conn, BANNER)
    send(conn, "[*] Binary: auth_node_4.elf — Contains a tiny custom VM.")
    send(conn, "[*] Trace the VM execution to find the password derivation.")
    send(conn, "[*] Hint: The VM is stack-based with PUSH, XOR, ADD, HALT opcodes.\n")
    send(conn, "Password: ")

    attempt = recv_line(conn)
    correct = bank4_password()
    if attempt != correct:
        send(conn, "\n[-] AUTHENTICATION FAILED.")
        conn.close()
        return

    sid = create_session(BANK_ID, ip)
    authenticate_session(sid)
    send(conn, "\n[+] WELCOME TO DESERT GOLD EXCHANGE.")
    send(conn, f"[*] Session: {sid}")
    send(conn, "[*] Exploit: Integer Overflow — amounts are stored as signed int32 cents.")
    send(conn, "[*] Send amount in CENTS (integer). Magic value: 2147483649")
    send(conn, "[*] (INT32_MAX + 2) overflows to -2147483647, abs remainder = 1 cent\n")

    while True:
        send(conn, "desert> ")
        cmd = recv_line(conn).strip()
        if not cmd:
            continue

        if cmd.lower() == "help":
            send(conn, "Commands: transfer <cents_int> | balance | token | exit")

        elif cmd.lower().startswith("transfer "):
            try:
                raw_cents = int(cmd.split()[1])
            except (IndexError, ValueError):
                send(conn, "[-] Usage: transfer <integer cents>")
                continue

            remainder = integer_wrap_exploit(raw_cents)
            if remainder == 1:
                stolen = 0.01
                result = record_theft(sid, stolen)
                if "error" in result:
                    send(conn, f"[-] {result['error']}")
                    if "locked" in result["error"]: break
                else:
                    send(conn, f"[+] Overflow triggered! 1¢ siphoned | Total: ${result['balance']:.2f} | Tx #{result['tx_count']}")
                    if result["completed"]:
                        send(conn, f"\n[!!!] $1,000.00 EXTRACTED")
                        send(conn, f"[*]  Token: {result['token']}")
                        break
            else:
                send(conn, f"[-] Transfer of {raw_cents} cents processed. No overflow. Remainder: {remainder}")

        elif cmd.lower() == "balance":
            from database import get_session
            s = get_session(sid)
            if s:
                send(conn, f"[*] Stolen: ${s['balance_stolen']:.2f} | Tx: {s['tx_count']}")

        elif cmd.lower() == "token":
            tok = get_token(sid)
            send(conn, f"[*] Token: {tok}" if tok else "[-] Keep going.")

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
    print(f"[Bank4-Desert] Listening on 0.0.0.0:{PORT}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
