/*
 * auth_node_4.elf — Desert Gold Exchange
 * Challenge: Custom stack-based VM executes bytecode to verify password
 *
 * VM Architecture:
 *   Stack-based, 8 opcodes
 *   Opcodes:
 *     0x05 <val>  PUSH — push 1-byte value onto stack
 *     0x03        XOR  — pop top two, push XOR result
 *     0x04        ADD  — pop top two, push ADD result
 *     0x06        ROT  — rotate top three stack elements
 *     0x01        HALT — stop execution
 *     0xFF        NOP  — no operation
 *
 * Bytecode: 05 4B 05 37 03 01
 *   PUSH 0x4B  → stack: [0x4B]
 *   PUSH 0x37  → stack: [0x4B, 0x37]
 *   XOR        → stack: [0x7C]  (0x4B ^ 0x37 = 0x7C)
 *   HALT
 *   Result: TOS = 0x7C → password = "DSGLD_7C7C"
 *
 * Players must:
 *   1. Identify the VM loop
 *   2. Trace the bytecode execution
 *   3. Derive the password: "DSGLD_7C7C"
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>

#define STACK_SIZE 64
#define OP_PUSH 0x05
#define OP_XOR  0x03
#define OP_ADD  0x04
#define OP_ROT  0x06
#define OP_HALT 0x01
#define OP_NOP  0xFF

/* Obfuscated bytecode — looks like binary data */
static const uint8_t BYTECODE[] = {
    0x05, 0x4B,   /* PUSH 0x4B */
    0x05, 0x37,   /* PUSH 0x37 */
    0x03,         /* XOR        */
    0x01          /* HALT       */
};
static const int BC_LEN = 6;

typedef struct {
    uint8_t data[STACK_SIZE];
    int     top;
} Stack;

static void stack_push(Stack *s, uint8_t v) {
    if (s->top < STACK_SIZE - 1) s->data[++s->top] = v;
}
static uint8_t stack_pop(Stack *s) {
    if (s->top < 0) return 0;
    return s->data[s->top--];
}

static uint8_t vm_execute(const uint8_t *bc, int len) {
    Stack s = { .top = -1 };
    int ip = 0;
    while (ip < len) {
        uint8_t op = bc[ip];
        switch (op) {
            case OP_PUSH:
                stack_push(&s, bc[ip+1]);
                ip += 2;
                break;
            case OP_XOR: {
                uint8_t a = stack_pop(&s);
                uint8_t b = stack_pop(&s);
                stack_push(&s, a ^ b);
                ip++;
                break;
            }
            case OP_ADD: {
                uint8_t a = stack_pop(&s);
                uint8_t b = stack_pop(&s);
                stack_push(&s, (a + b) & 0xFF);
                ip++;
                break;
            }
            case OP_ROT: {
                /* rotate top 3: [a, b, c] → [b, c, a] */
                if (s.top >= 2) {
                    uint8_t c = stack_pop(&s);
                    uint8_t b = stack_pop(&s);
                    uint8_t a = stack_pop(&s);
                    stack_push(&s, b);
                    stack_push(&s, c);
                    stack_push(&s, a);
                }
                ip++;
                break;
            }
            case OP_HALT:
                goto done;
            case OP_NOP:
            default:
                ip++;
                break;
        }
    }
done:;
    return (s.top >= 0) ? s.data[s.top] : 0;
}

int main(void) {
    uint8_t result = vm_execute(BYTECODE, BC_LEN);

    /* Password derived from VM result */
    char password[32];
    snprintf(password, sizeof(password), "DSGLD_%02X7C", result);

    printf("╔══════════════════════════════════════════╗\n");
    printf("║   DESERT GOLD EXCHANGE — AUTH CLIENT     ║\n");
    printf("║   Protected by DG-VM v1.2                ║\n");
    printf("╚══════════════════════════════════════════╝\n\n");
    printf("Password: ");
    fflush(stdout);

    char input[256] = {0};
    if (!fgets(input, sizeof(input), stdin)) return 1;
    input[strcspn(input, "\n")] = 0;

    if (strcmp(input, password) == 0) {
        printf("[+] VM AUTHENTICATION SUCCESSFUL.\n");
        return 0;
    } else {
        printf("[-] VM AUTHENTICATION FAILED.\n");
        return 1;
    }
}
