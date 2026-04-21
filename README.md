# 🏦 CTF Challenge: One Cent Thief

> **"Five banks. Five tokens. One masterpiece."**

A Black Badge–level CTF combining Reverse Engineering, Scripting, and Logic exploitation.

---

## 🗺 Challenge Overview

| Phase | Task | Skills Required |
|-------|------|-----------------|
| 1 | Reverse-engineer 5 auth binaries | RE: XOR, HMAC, anti-debug, custom VM, PoW |
| 2 | Siphon $1,000 via rounding exploits | Python scripting, number theory, side-channel |
| 3 | Submit 5 tokens to The Broker | OSINT/logic, rate-limit awareness |

**Flag format:** `ronin{...}` — but the Broker delivers it **AES-128-CBC encrypted**. Players must decrypt the ciphertext to read the flag.

> *"I don't hand out plaintext. That's not how this business works."*

---

## 🏗 Architecture

```
.
├── backend/
│   ├── database.py        # SQLite session + broker tracking
│   └── passwords.py       # Dynamic password derivation for all 5 banks
├── banks/
│   ├── bank1_ironclad/    # XOR encryption — Banker's Rounding exploit
│   ├── bank2_sakura/      # HMAC-SHA1 TOTP — IEEE 754 exploit
│   ├── bank3_swiss/       # Anti-debug + .rsrc — Currency Loop + side-channel
│   ├── bank4_desert/      # Custom VM — Integer Overflow exploit
│   └── bank5_nero/        # Proof-of-Work — Banker's Rounding v2 exploit
├── broker/
│   └── server.py          # Final flag exchange — 3-attempt lockout
├── binaries/
│   ├── src/               # C source for all 5 auth binaries
│   └── build.sh           # Compile script
├── scripts/               # Player exploit scripts (for CTF authors/testers)
│   ├── solve_bank1.py
│   ├── solve_bank2.py
│   ├── solve_bank3.py
│   ├── solve_bank4.py
│   ├── solve_bank5.py
│   └── submit_broker.py
├── docker/
│   ├── Dockerfile.bank
│   └── Dockerfile.broker
└── docker-compose.yml
```

---

## 🚀 Deployment

### Prerequisites
- Docker & Docker Compose
- GCC (for compiling binaries)

### 1. Build Auth Binaries
```bash
cd binaries
chmod +x build.sh
./build.sh
# Binaries appear in binaries/compiled/
```

### 2. Launch Challenge
```bash
docker-compose up --build -d
```

### 3. Verify Services
```bash
docker-compose ps
nc localhost 9001   # Bank 1
nc localhost 9999   # Broker
```

### 4. Distribute Binaries
Host `binaries/compiled/auth_node_[1-5].elf` on your challenge server for players to download.

---

## 🎯 Bank Details

### Bank 1 — Ironclad National `:9001`
- **Auth:** XOR-encrypted password in binary. Key: `0xDEADBEEFCAFEBABE`
- **Password:** `ironfort` (decoded from cipher bytes)
- **Exploit:** Banker's Rounding — send `0.0150000000001`

### Bank 2 — Sakura Financial `:9002`
- **Auth:** HMAC-SHA1(secret, epoch//60) → first 8 hex chars. Rotates every 60s.
- **Secret:** `sakura_temporal_seed_v2`
- **Exploit:** IEEE 754 — send `0.010000001192092896` (float64 → float32 loses $0.01)

### Bank 3 — Swiss Vault AG `:9003`
- **Auth:** Password in `.rsrc` ELF section — `Sw1ssV@ult#9`. Anti-debug in binary.
- **Exploit:** Currency Loop — truncated USD→EUR→USD conversion leaks $0.01
- **Side-Channel:** No error messages. ~50ms = success, ~20ms = fail.

### Bank 4 — Desert Gold Exchange `:9004`
- **Auth:** Custom stack-based VM — trace bytecode `05 4B 05 37 03 01` → `DSGLD_7C7C`
- **Exploit:** Integer Overflow — send `2147483649` (INT32_MAX+2) wraps to remainder 1¢

### Bank 5 — Nero Digital `:9005`
- **Auth:** Solve SHA256 PoW (5 leading zeros), derive session password from nonce
- **Challenge string:** `NERO_DIGITAL_2077`
- **Exploit:** Banker's Rounding — `0.005` rounds to `0.00` but ledger posts `$0.01`

### The Broker `:9999`
- Submit all 5 tokens to receive the **encrypted flag**
- **3 wrong token attempts = session locked + all sessions invalidated + passwords rotate**
- Players must re-authenticate all 5 banks from scratch
- The Broker delivers `AES-128-CBC` ciphertext — players must derive the **16-char key** from clues scattered across the 5 banks

#### Flag Encryption
```
Algorithm  : AES-128-CBC
Key        : OneCentThiefKey!   (assembled from per-bank key fragments)
IV         : SalamiSliceIV!!!   (hinted by the challenge theme)
Plaintext  : ronin{0n3_C3nt_5_B4nk5_0n3_M45t3rm1nd_92}
Ciphertext : 8TeTSXbc7AAYIOkU+fAWIB+iG4tJ4Q2xKrEe3zFBYPljupi9DPPj13N8mP+8wqhz
```

Decrypt snippet:
```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64
key = b'OneCentThiefKey!'
iv  = base64.b64decode('U2FsYW1pU2xpY2VJViEhIQ==')
ct  = base64.b64decode('8TeTSXbc7AAYIOkU+fAWIB+iG4tJ4Q2xKrEe3zFBYPljupi9DPPj13N8mP+8wqhz')
print(unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(ct), 16).decode())
# ronin{0n3_C3nt_5_B4nk5_0n3_M45t3rm1nd_92}
```

---

## ⚔️ Security Features

| Feature | Details |
|---------|---------|
| IDS Rate Limiting | >200 req/s → account locked |
| Broker Lockout | 3 wrong tokens → session killed + full reset |
| Dynamic Passwords | Bank 2 rotates every 60s; all rotate on broker lockout |
| Anti-Debug | Bank 3: ptrace check + /proc/status TracerPid + timing |
| Side-Channel | Bank 3: no error messages, response time encodes result |
| PoW Gate | Bank 5: must solve SHA256 with 5 leading zeros first |

---

## 🔧 Testing (CTF Author)

Reference solver scripts are in `scripts/`. Run all five banks, then submit:
```bash
# In separate terminals or sequentially:
python3 scripts/solve_bank1.py localhost
python3 scripts/solve_bank2.py localhost
python3 scripts/solve_bank3.py localhost
python3 scripts/solve_bank4.py localhost
python3 scripts/solve_bank5.py localhost

# Tokens written to tokens.txt — submit to broker:
python3 scripts/submit_broker.py localhost
```

---

## 📝 Notes for CTF Hosts

1. **SQLite is shared** via Docker volume — all containers write to `/data/ctf.db`
2. **Reset the challenge** by deleting the volume: `docker-compose down -v`
3. **Per-team isolation**: Spawn separate docker-compose stacks with different ports per team
4. **Binary distribution**: Serve `binaries/compiled/` via HTTP (e.g., nginx) alongside the challenge description

---

*"You don't steal a million. You steal a penny, a million times."*
