#include "kasa.h"
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "lwip/sockets.h"
#include "wifi.h"

#define PORT 9999

static TaskHandle_t task;
static char ip[16]; /* empty until discovery finds the switch */
static char status[80] = "Kasa: waiting for Wi-Fi";

/* Kasa's cipher: each byte is XORed with the previous ciphertext byte, starting from 171. */
static void obfuscate(char *d, int n)
{
    unsigned char k = 171;
    for (int i = 0; i < n; i++) k = d[i] ^= k;
}

static void reveal(char *d, int n)
{
    unsigned char k = 171;
    for (int i = 0; i < n; i++) {
        unsigned char c = d[i];
        d[i] ^= k;
        k = c;
    }
}

static const char SYSINFO[] = "{\"system\":{\"get_sysinfo\":{}}}";

/* Broadcasts a sysinfo request and takes the address of whichever device answers with
 * our alias. */
static bool discover(void)
{
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    if (s < 0) return false;
    int yes = 1;
    setsockopt(s, SOL_SOCKET, SO_BROADCAST, &yes, sizeof yes);
    struct timeval tv = {.tv_sec = 0, .tv_usec = 500000};
    setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv);
    struct sockaddr_in to = {.sin_family = AF_INET, .sin_port = htons(PORT), .sin_addr.s_addr = INADDR_BROADCAST};
    char q[sizeof SYSINFO];
    memcpy(q, SYSINFO, sizeof q);
    obfuscate(q, sizeof q - 1);

    bool found = false;
    static char buf[2048];
    for (int attempt = 0; attempt < 3 && !found; attempt++) {
        sendto(s, q, sizeof q - 1, 0, (struct sockaddr *)&to, sizeof to);
        struct sockaddr_in from;
        socklen_t len = sizeof from;
        int n;
        while ((n = recvfrom(s, buf, sizeof buf - 1, 0, (struct sockaddr *)&from, &len)) > 0) {
            reveal(buf, n);
            buf[n] = 0;
            if (strstr(buf, "\"alias\":\"" KASA_ALIAS "\"")) {
                inet_ntoa_r(from.sin_addr, ip, sizeof ip);
                found = true;
                break;
            }
        }
    }
    close(s);
    return found;
}

/* Sends one command over TCP and reads the reply into buf. TCP frames each message with
 * its length as four big-endian bytes. */
static bool command(const char *json, char *buf, int size)
{
    int s = socket(AF_INET, SOCK_STREAM, 0);
    if (s < 0) return false;
    struct timeval tv = {.tv_sec = 2};
    setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv);
    setsockopt(s, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof tv);
    struct sockaddr_in to = {.sin_family = AF_INET, .sin_port = htons(PORT)};
    inet_aton(ip, &to.sin_addr);
    bool ok = false;
    if (connect(s, (struct sockaddr *)&to, sizeof to) == 0) {
        int n = strlen(json);
        char q[4 + 128];
        q[0] = n >> 24, q[1] = n >> 16, q[2] = n >> 8, q[3] = n;
        memcpy(q + 4, json, n);
        obfuscate(q + 4, n);
        if (send(s, q, 4 + n, 0) == 4 + n) {
            unsigned char head[4];
            if (recv(s, head, 4, MSG_WAITALL) == 4) {
                int len = head[0] << 24 | head[1] << 16 | head[2] << 8 | head[3];
                if (len < size && recv(s, buf, len, MSG_WAITALL) == len) {
                    reveal(buf, len);
                    buf[len] = 0;
                    ok = true;
                }
            }
        }
    }
    close(s);
    return ok;
}

/* Reads the relay state and sets the opposite. Returns the new state, or -1. */
static int toggle_once(void)
{
    static char buf[2048];
    if (!command(SYSINFO, buf, sizeof buf)) return -1;
    char *p = strstr(buf, "\"relay_state\":");
    if (!p) return -1;
    int on = p[14] == '1';
    char set[64];
    snprintf(set, sizeof set, "{\"system\":{\"set_relay_state\":{\"state\":%d}}}", !on);
    if (!command(set, buf, sizeof buf) || !strstr(buf, "\"err_code\":0")) return -1;
    return !on;
}

static void run(void *arg)
{
    for (;;) {
        bool asked = ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(ip[0] ? portMAX_DELAY : 2000));
        if (!wifi_address()) continue;
        if (!ip[0]) {
            if (!discover()) {
                snprintf(status, sizeof status, "Kasa: \"%s\" not found on the network yet", KASA_ALIAS);
                continue;
            }
            snprintf(status, sizeof status, "Kasa: \"%s\" at %s", KASA_ALIAS, ip);
        }
        if (!asked) continue;
        int on = toggle_once();
        if (on < 0) { /* the address may have changed: find it again and retry once */
            ip[0] = 0;
            if (discover()) on = toggle_once();
        }
        if (on < 0)
            snprintf(status, sizeof status, "Kasa: could not reach \"%s\"", KASA_ALIAS);
        else
            snprintf(status, sizeof status, "Kasa: \"%s\" at %s, turned %s", KASA_ALIAS, ip, on ? "on" : "off");
    }
}

void kasa_start(void) { xTaskCreate(run, "kasa", 6144, NULL, 5, &task); }

void kasa_toggle(void)
{
    if (task) xTaskNotifyGive(task);
}

const char *kasa_status(void) { return status; }
