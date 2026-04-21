/*
 * auth_node_2.elf — Sakura Financial Group
 * Challenge: Time-based HMAC-SHA1 password (rotates every 60 seconds)
 *
 * Players must:
 *   1. Find the HMAC secret: "sakura_temporal_seed_v2"
 *   2. Understand the time-window: floor(time() / 60)
 *   3. Compute SHA1(secret + BE64(window)) → first 8 hex chars = password
 *
 * This binary mimics a TOTP-like authenticator.
 * Players cannot just "find the string" — they must implement the logic.
 *
 * SHA1 implementation is inline to avoid dynamic linking hints.
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>

/* ---------- Minimal SHA1 ---------- */
typedef struct { uint32_t state[5]; uint64_t count; uint8_t buf[64]; } SHA1_CTX;

#define ROL32(x,n) (((x)<<(n))|((x)>>(32-(n))))

static void sha1_transform(SHA1_CTX *ctx, const uint8_t data[]) {
    uint32_t a,b,c,d,e,f,k,tmp,w[80];
    int i;
    for(i=0;i<16;i++) w[i]=((uint32_t)data[i*4]<<24)|((uint32_t)data[i*4+1]<<16)|((uint32_t)data[i*4+2]<<8)|(uint32_t)data[i*4+3];
    for(;i<80;i++) w[i]=ROL32(w[i-3]^w[i-8]^w[i-14]^w[i-16],1);
    a=ctx->state[0];b=ctx->state[1];c=ctx->state[2];d=ctx->state[3];e=ctx->state[4];
    for(i=0;i<80;i++){
        if(i<20){f=(b&c)|(~b&d);k=0x5A827999;}
        else if(i<40){f=b^c^d;k=0x6ED9EBA1;}
        else if(i<60){f=(b&c)|(b&d)|(c&d);k=0x8F1BBCDC;}
        else{f=b^c^d;k=0xCA62C1D6;}
        tmp=ROL32(a,5)+f+e+k+w[i];e=d;d=c;c=ROL32(b,30);b=a;a=tmp;
    }
    ctx->state[0]+=a;ctx->state[1]+=b;ctx->state[2]+=c;ctx->state[3]+=d;ctx->state[4]+=e;
}
static void sha1_init(SHA1_CTX *ctx){
    ctx->count=0;
    ctx->state[0]=0x67452301;ctx->state[1]=0xEFCDAB89;
    ctx->state[2]=0x98BADCFE;ctx->state[3]=0x10325476;ctx->state[4]=0xC3D2E1F0;
}
static void sha1_update(SHA1_CTX *ctx,const uint8_t *d,size_t len){
    size_t i=0,j=ctx->count%64;
    ctx->count+=len;
    if(j+len>63){memcpy(&ctx->buf[j],d,64-j);sha1_transform(ctx,ctx->buf);for(i=64-j;i+63<len;i+=64)sha1_transform(ctx,d+i);j=0;}
    memcpy(&ctx->buf[j],d+i,len-i);
}
static void sha1_final(SHA1_CTX *ctx,uint8_t digest[20]){
    uint8_t fin[8];uint64_t cnt=ctx->count*8;
    sha1_update(ctx,(uint8_t*)"\x80",1);
    while(ctx->count%64!=56)sha1_update(ctx,(uint8_t*)"\0",1);
    for(int i=7;i>=0;i--){fin[i]=(uint8_t)(cnt&0xff);cnt>>=8;}
    sha1_update(ctx,fin,8);
    for(int i=0;i<5;i++){digest[i*4]=(ctx->state[i]>>24)&0xff;digest[i*4+1]=(ctx->state[i]>>16)&0xff;digest[i*4+2]=(ctx->state[i]>>8)&0xff;digest[i*4+3]=ctx->state[i]&0xff;}
}
/* ---------------------------------- */

/* Obfuscated secret — in binary as bytes, not string literal */
static const unsigned char SECRET[] = {
    0x73,0x61,0x6b,0x75,0x72,0x61,0x5f,0x74,
    0x65,0x6d,0x70,0x6f,0x72,0x61,0x6c,0x5f,
    0x73,0x65,0x65,0x64,0x5f,0x76,0x32
}; /* "sakura_temporal_seed_v2" */

int main(void) {
    time_t now = time(NULL);
    uint64_t window = (uint64_t)(now / 60);
    int remaining  = 60 - (int)(now % 60);

    /* Build HMAC input: secret + big-endian window */
    uint8_t msg[31];
    memcpy(msg, SECRET, 23);
    for(int i=0;i<8;i++) msg[23+i] = (uint8_t)((window >> (56-8*i)) & 0xff);

    SHA1_CTX ctx; uint8_t digest[20];
    sha1_init(&ctx);
    sha1_update(&ctx, msg, 31);
    sha1_final(&ctx, digest);

    char hex[41];
    for(int i=0;i<20;i++) sprintf(hex+i*2,"%02x",digest[i]);
    hex[40]='\0';

    printf("╔══════════════════════════════════════════╗\n");
    printf("║   SAKURA FINANCIAL — AUTH CLIENT         ║\n");
    printf("╚══════════════════════════════════════════╝\n\n");
    printf("[*] Password window expires in %d seconds.\n", remaining);
    printf("[*] Current password: %.8s\n", hex);
    printf("[*] Use this within the time window to authenticate.\n");
    return 0;
}
