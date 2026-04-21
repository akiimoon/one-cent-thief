"""
Dynamic password generation for all 5 banks.
Passwords are re-generated when a session is invalidated (3 wrong broker attempts).
"""
import time
import hashlib
import struct

# ── Bank 1: Ironclad — XOR encrypted hardcoded password ─────────────────────
_XOR_KEY = b"\xDE\xAD\xBE\xEF\xCA\xFE\xBA\xBE"
_XOR_CIPHER = bytes([0xB7, 0xDF, 0xD1, 0x81, 0xAC, 0x91, 0xC8, 0xCA])  # "ironfort" XOR'd with key

def bank1_password() -> str:
    result = bytes([_XOR_CIPHER[i] ^ _XOR_KEY[i % len(_XOR_KEY)] for i in range(len(_XOR_CIPHER))])
    return result.decode("latin-1")


# ── Bank 2: Sakura — HMAC-SHA1 of current 60-second epoch window ─────────────
_SAKURA_SECRET = b"sakura_temporal_seed_v2"

def bank2_password() -> str:
    window = int(time.time()) // 60
    h = hashlib.sha1(_SAKURA_SECRET + struct.pack(">Q", window)).hexdigest()
    return h[:8]


def bank2_time_remaining() -> int:
    return 60 - (int(time.time()) % 60)


# ── Bank 3: Swiss Vault — hidden in binary resource section ──────────────────
_SWISS_RESOURCE = "Sw1ssV@ult#9"

def bank3_password() -> str:
    return _SWISS_RESOURCE


# ── Bank 4: Desert Gold — custom VM interprets bytecode ──────────────────────
# VM: stack-based, ops: PUSH(val), XOR(top two), ADD(top two), HALT → password is hex(tos)
_DESERT_BYTECODE = [0x05, 0x4B, 0x05, 0x37, 0x03, 0x01]  # PUSH 0x4B, PUSH 0x37, XOR, HALT → 0x7C

def bank4_password() -> str:
    stack = []
    i = 0
    bc = _DESERT_BYTECODE
    while i < len(bc):
        op = bc[i]
        if op == 0x05:   # PUSH next byte
            i += 1
            stack.append(bc[i])
            i += 1
        elif op == 0x03: # XOR top two
            if len(stack) >= 2:
                a = stack.pop(); b = stack.pop(); stack.append(a ^ b)
            i += 1
        elif op == 0x01: # HALT
            break
        else:
            i += 1
    # password = hex result padded + static suffix
    result = stack[0] if stack else 0
    return f"DSGLD_{result:02X}7C"


# ── Bank 5: Nero Digital — PoW: sha256(nonce + challenge)[:5] == "00000" ────
_NERO_CHALLENGE = "NERO_DIGITAL_2077"

def bank5_challenge() -> str:
    return _NERO_CHALLENGE

def bank5_verify_pow(nonce: str) -> bool:
    h = hashlib.sha256(f"{nonce}{_NERO_CHALLENGE}".encode()).hexdigest()
    return h.startswith("00000")

def bank5_password(nonce: str) -> str:
    """After PoW, password is derived from nonce."""
    if not bank5_verify_pow(nonce):
        return ""
    h = hashlib.sha256(f"NERO_SESSION_{nonce}".encode()).hexdigest()
    return h[:10]
