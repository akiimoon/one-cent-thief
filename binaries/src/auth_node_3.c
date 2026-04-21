/*
 * auth_node_3.elf — Swiss Vault AG
 * Challenge: Anti-debugging + password hidden in .rsrc section
 *
 * Anti-debug techniques:
 *   1. ptrace(PTRACE_TRACEME) — fails if already being traced
 *   2. /proc/self/status TracerPid check
 *   3. Timing attack: if execution is too slow (debugger), exit
 *
 * Password: "Sw1ssV@ult#9" (stored in custom .rsrc ELF section)
 *
 * Players must:
 *   1. Bypass or patch anti-debug checks
 *   2. Find and read the .rsrc section
 *   3. Use the password on the nc server
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/ptrace.h>
#include <sys/time.h>
#include <fcntl.h>

/* Anti-debug: ptrace self-trace check */
static int is_traced_ptrace(void) {
#ifdef __linux__
    if (ptrace(PTRACE_TRACEME, 0, 0, 0) == -1) {
        return 1; /* already being traced */
    }
    ptrace(PTRACE_DETACH, 0, 0, 0);
#endif
    return 0;
}

/* Anti-debug: /proc/self/status TracerPid */
static int is_traced_proc(void) {
    FILE *f = fopen("/proc/self/status", "r");
    if (!f) return 0;
    char line[256];
    while (fgets(line, sizeof(line), f)) {
        if (strncmp(line, "TracerPid:", 10) == 0) {
            fclose(f);
            int pid = atoi(line + 10);
            return pid != 0;
        }
    }
    fclose(f);
    return 0;
}

/* Anti-debug: timing check — debugger slows execution > 500ms */
static int is_timed_out(struct timeval *start) {
    struct timeval now;
    gettimeofday(&now, NULL);
    long elapsed_ms = (now.tv_sec - start->tv_sec) * 1000
                    + (now.tv_usec - start->tv_usec) / 1000;
    return elapsed_ms > 500;
}

/*
 * Password stored in custom ELF section ".rsrc"
 * Players need to: readelf -x .rsrc auth_node_3.elf
 * or use: objdump -s -j .rsrc auth_node_3.elf
 */
__attribute__((section(".rsrc")))
static const char VAULT_PASSWORD[] = "Sw1ssV@ult#9";

int main(void) {
    struct timeval start;
    gettimeofday(&start, NULL);

    printf("╔══════════════════════════════════════════╗\n");
    printf("║   SWISS VAULT AG — AUTH CLIENT           ║\n");
    printf("║   WARNING: Anti-debug protection active  ║\n");
    printf("╚══════════════════════════════════════════╝\n\n");

    /* Anti-debug checks */
    if (is_traced_ptrace()) {
        printf("[-] Debugger detected (ptrace). Exiting.\n");
        return 2;
    }
    if (is_traced_proc()) {
        printf("[-] Tracer detected (/proc). Exiting.\n");
        return 2;
    }

    char input[256] = {0};
    printf("Password: ");
    fflush(stdout);

    if (!fgets(input, sizeof(input), stdin)) return 1;
    input[strcspn(input, "\n")] = 0;

    /* Timing check after input */
    if (is_timed_out(&start)) {
        printf("[-] Execution anomaly detected. Exiting.\n");
        return 2;
    }

    if (strcmp(input, VAULT_PASSWORD) == 0) {
        printf("[+] VAULT ACCESS GRANTED.\n");
        return 0;
    } else {
        /* Swiss Vault: NO error message — just silence */
        return 1;
    }
}
