#!/usr/bin/env python3
"""
Broker Token Submission Script
Reads tokens from tokens.txt (written by solve_bankN.py scripts)
Submits them to The Broker to claim the final flag.

Usage: python3 submit_broker.py <host> [port]
"""
import socket, sys, os

HOST = sys.argv[1] if len(sys.argv) > 1 else "localhost"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9999


def load_tokens():
    tokens = []
    if not os.path.exists("tokens.txt"):
        print("[-] tokens.txt not found. Run all 5 bank solvers first.")
        return []
    with open("tokens.txt") as f:
        for line in f:
            line = line.strip()
            if ":" in line:
                _, tok = line.split(":", 1)
                tokens.append(tok.strip())
    return tokens


def solve():
    tokens = load_tokens()
    if not tokens:
        return

    print(f"[*] Loaded {len(tokens)} token(s): {tokens}")
    print(f"[*] Connecting to Broker at {HOST}:{PORT}")

    s = socket.socket()
    s.connect((HOST, PORT))
    s.settimeout(15)

    buf = b""
    while b"broker> " not in buf:
        buf += s.recv(4096)
    print(buf.decode(errors="replace").strip())

    for token in tokens:
        print(f"\n[*] Submitting: {token}")
        s.sendall(f"submit {token}\n".encode())
        resp = b""
        while b"broker> " not in resp and b"FLAG:" not in resp and b"TERMINATED" not in resp:
            resp += s.recv(4096)
        resp_str = resp.decode(errors="replace")
        print(resp_str.strip())

        if "FLAG:" in resp_str:
            for line in resp_str.split("\n"):
                if "FLAG:" in line:
                    print(f"\n{'='*60}")
                    print(f"  {line.strip()}")
                    print(f"{'='*60}\n")
            s.close()
            return

        if "TERMINATED" in resp_str or "LOCKOUT" in resp_str.upper():
            print("[-] Session terminated. All passwords rotated. Start over.")
            s.close()
            return

    # Check status
    s.sendall(b"status\n")
    resp = b""
    while b"broker> " not in resp:
        resp += s.recv(4096)
    print(resp.decode(errors="replace").strip())
    s.sendall(b"exit\n")
    s.close()


if __name__ == "__main__":
    solve()
