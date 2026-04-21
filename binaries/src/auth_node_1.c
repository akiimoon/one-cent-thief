/*
 * auth_node_1.elf — Ironclad National Bank
 * Authentication binary for players to reverse-engineer.
 *
 * Challenge: XOR-encrypted password.
 * Key:    0xDE 0xAD 0xBE 0xEF 0xCA 0xFE 0xBA 0xBE
 * Cipher: 0x96 0xCC 0xD3 0x89 0xA5 0xC2 0xCF 0xCF
 * Result: "ironfort" (decode to find the password)
 *
 * Players must reverse-engineer this binary to extract:
 *   1. The XOR key
 *   2. The encrypted bytes
 *   3. XOR them to get the plaintext password
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* Obfuscated: these look like random data in the binary */
static const unsigned char KEY[]    = {0xDE, 0xAD, 0xBE, 0xEF, 0xCA, 0xFE, 0xBA, 0xBE};
static const unsigned char CIPHER[] = {0xB7, 0xDF, 0xD1, 0x81, 0xAC, 0x91, 0xC8, 0xCA};  /* XOR of "ironfort" with KEY */
static const int LEN = 8;

/* Anti-string: password never appears as plaintext in the binary */
static void decode(char *out) {
    for (int i = 0; i < LEN; i++) {
        out[i] = (char)(CIPHER[i] ^ KEY[i % LEN]);
    }
    out[LEN] = '\0';
}

/* Dummy function to confuse static analysis */
static int check_env(void) {
    /* Always returns 0 — just bloat */
    char *dbg = getenv("LD_PRELOAD");
    if (dbg && strlen(dbg) > 0) return 1;
    return 0;
}

int main(void) {
    char decoded[16] = {0};
    char input[256]  = {0};

    printf("╔══════════════════════════════════════════╗\n");
    printf("║    IRONCLAD NATIONAL — AUTH CLIENT       ║\n");
    printf("╚══════════════════════════════════════════╝\n\n");
    printf("Password: ");
    fflush(stdout);

    if (!fgets(input, sizeof(input), stdin)) {
        return 1;
    }
    /* Strip newline */
    input[strcspn(input, "\n")] = 0;

    decode(decoded);

    if (check_env()) {
        printf("[-] Environment anomaly detected.\n");
        return 1;
    }

    if (strcmp(input, decoded) == 0) {
        printf("[+] ACCESS GRANTED — Connect to nc server with this password.\n");
        return 0;
    } else {
        printf("[-] ACCESS DENIED.\n");
        return 1;
    }
}
