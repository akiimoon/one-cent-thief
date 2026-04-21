#!/bin/bash
# Compile all 5 auth binaries for Linux x86_64
# Run from: binaries/

set -e
SRC="src"
OUT="compiled"

echo "[*] Building auth binaries..."

# Bank 1 — Ironclad (XOR password, strip symbols)
gcc -O2 -s -o "$OUT/auth_node_1.elf" "$SRC/auth_node_1.c"
echo "[+] auth_node_1.elf built"

# Bank 2 — Sakura (SHA1 TOTP, strip symbols)
gcc -O2 -s -o "$OUT/auth_node_2.elf" "$SRC/auth_node_2.c"
echo "[+] auth_node_2.elf built"

# Bank 3 — Swiss Vault (anti-debug + .rsrc section)
gcc -O2 -s \
    -Wl,--section-start=.rsrc=0x500000 \
    -o "$OUT/auth_node_3.elf" "$SRC/auth_node_3.c"
echo "[+] auth_node_3.elf built"

# Bank 4 — Desert Gold (custom VM)
gcc -O2 -s -o "$OUT/auth_node_4.elf" "$SRC/auth_node_4.c"
echo "[+] auth_node_4.elf built"

# Bank 5 — Nero Digital (SHA256 PoW)
gcc -O2 -s -o "$OUT/auth_node_5.elf" "$SRC/auth_node_5.c"
echo "[+] auth_node_5.elf built"

echo ""
echo "[*] All binaries compiled to $OUT/"
echo "[*] Deploy these to your challenge server for players to download."
