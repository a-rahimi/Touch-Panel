/* Shows the MPR121's 12 readings as a 3 x 4 grid laid out like the panel seen from
 * the front and turned 180 degrees, so with ELE0 at the bottom right, redrawn in
 * place 20 times a second.
 *
 * Each cell shows how far its electrode's reading is from its background, coloured
 * from grey (nothing near) through blue, green and yellow to red (FULL_SCALE or more),
 * with the raw filtered reading beneath. The background is a first-order low-pass of
 * the electrode's past readings, with time constant BACKGROUND_S, so slow drift drops
 * out of the change. It holds still while any pad's change is above HAND_GATE, so a
 * hand does not drag it down: otherwise repeated gestures leave the idle readings
 * several counts negative. If the gate stays shut for HOLD_MAX_S, which a hand would
 * not do, the background updates anyway, so drift cannot freeze it for good. The
 * MPR121's own averaging already removes the fastest noise, so the change is the
 * reading band-passed. A hand lowers the raw reading, so the change shown is
 * background minus reading, and it grows as the hand comes closer.
 *
 * The pad token is the pad whose centre the centroid is within TOKEN_RADIUS of, in
 * cells, or -1 while the dot is between pads, or -2 while there is no dot. The display
 * shows it with the recent sequence of tokens, each written once when it changes:
 * the pad number, "-" for between pads and "." for no hand.
 *
 * A bright red dot marks the centroid of the changes above NOISE, each electrode
 * weighted by how far its change exceeds NOISE, placed between cell centres.
 *
 * Under the grid, how much of the gesture 2+1+0+1+2+ the tokens have matched so far
 * (gesture.h), and a banner for a second after it completes.
 *
 * Sending r switches to a plain stream, one line per frame:
 * "C,<frame>,<12 changes>,<pad token>,<1 if the gesture completed>". Sending g
 * switches back.
 *
 * While the dot shows, its position goes out over Bluetooth LE as well (ble.h).
 *
 * Each time the gesture completes, the Kasa switch KASA_ALIAS on the Wi-Fi is toggled
 * (kasa.h), except in the stream mode. Sending t toggles it by hand.
 *
 * The background starts as the average of the first BASELINE_READS readings, so keep
 * hands away while the firmware starts. Sending b over USB restarts it the same way. */
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "driver/usb_serial_jtag.h"
#include "driver/usb_serial_jtag_vfs.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "ble.h"
#include "gesture.h"
#include "kasa.h"
#include "mpr121.h"
#include "wifi.h"

#define PERIOD_MS 50
#define BASELINE_READS 16
#define BACKGROUND_S 10.0f /* untuned: the low-pass time constant of the background */
#define HAND_GATE 3        /* counts: above the noise of about 2, so only a hand shuts it */
#define HOLD_MAX_S 30
#define CELL_W_IN 4.0f    /* the pad grid's pitch across and down, in inches */
#define CELL_H_IN 3.75f
#define TOKEN_RADIUS 0.4f /* cells: below 0.5, so a dot between two pads hits neither */
#define HISTORY 40        /* characters of recent tokens shown */
#define FULL_SCALE 60 /* untuned: the change that shows as full red */
#define NOISE 2       /* a change this small or smaller stays grey */
#define COLS 3
#define ROWS 4
#define CELL_W 14
#define TOP 4 /* screen line where the grid starts, after the header */
#define BANNER_FRAMES 20

static float background[MPR121_ELECTRODES];

/* xterm 256-colour backgrounds, from cold to hot. */
static const uint8_t ramp[] = {17, 18, 19, 20, 21, 27, 33, 39, 45, 51, 49, 48, 47, 46,
                               82, 118, 154, 190, 226, 220, 214, 208, 202, 196};
#define RAMP_N (sizeof ramp / sizeof ramp[0])

static void take_baseline(void)
{
    uint16_t r[MPR121_ELECTRODES];
    memset(background, 0, sizeof background);
    int n = 0;
    while (n < BASELINE_READS) {
        vTaskDelay(pdMS_TO_TICKS(PERIOD_MS / 2));
        if (mpr121_read(r) != ESP_OK) continue;
        for (int e = 0; e < MPR121_ELECTRODES; e++) background[e] += r[e];
        n++;
    }
    for (int e = 0; e < MPR121_ELECTRODES; e++) background[e] /= BASELINE_READS;
}

/* Sets the background for a change, and black or white text to read against it. */
static void colour(int change)
{
    if (change <= NOISE) {
        printf("\033[48;5;236m\033[38;5;250m");
        return;
    }
    int i = (change - NOISE) * (int)(RAMP_N - 1) / (FULL_SCALE - NOISE);
    if (i > (int)RAMP_N - 1) i = RAMP_N - 1;
    printf("\033[48;5;%dm\033[38;5;%dm", ramp[i], i >= 9 ? 16 : 231);
}

/* The change of each electrode from its background, which then moves toward this
 * reading unless a hand is present. */
static void filter(const uint16_t r[MPR121_ELECTRODES], int change[MPR121_ELECTRODES])
{
    static int held;
    const float a = PERIOD_MS / 1000.0f / BACKGROUND_S;
    bool hand = false;
    for (int e = 0; e < MPR121_ELECTRODES; e++) {
        change[e] = (int)lroundf(background[e] - r[e]);
        if (change[e] > HAND_GATE) hand = true;
    }
    held = hand ? held + 1 : 0;
    if (hand && held * PERIOD_MS < HOLD_MAX_S * 1000) return;
    for (int e = 0; e < MPR121_ELECTRODES; e++) background[e] += a * (r[e] - background[e]);
}

/* The centroid of the changes above NOISE, in the panel's own rows and columns seen
 * from the front (ELE0 at row 0, column 0), or false if no pad is above NOISE. */
static bool panel_centroid(const int change[MPR121_ELECTRODES], float *row, float *col)
{
    float sum = 0;
    *row = *col = 0;
    for (int e = 0; e < MPR121_ELECTRODES; e++) {
        int w = change[e] - NOISE;
        if (w <= 0) continue;
        sum += w;
        *row += w * (e / COLS);
        *col += w * (e % COLS);
    }
    if (sum == 0) return false;
    *row /= sum;
    *col /= sum;
    return true;
}

/* The pad under the centroid: -1 if the centroid is not within TOKEN_RADIUS of any
 * pad's centre, and -2 if there is no centroid. */
static int token(bool dot, float row, float col)
{
    if (!dot) return -2;
    for (int e = 0; e < MPR121_ELECTRODES; e++)
        if (hypotf(row - e / COLS, col - e % COLS) < TOKEN_RADIUS) return e;
    return -1;
}

/* Recent tokens, one entry per change of token: "2 - 1 - 0 . 0 - 1 - 2". */
static char history[HISTORY + 1];

static void remember(int t)
{
    static int last = -3;
    if (t == last) return;
    last = t;
    char add[12];
    if (t >= 0)
        snprintf(add, sizeof add, "%d", t);
    else
        strcpy(add, t == -1 ? "-" : ".");
    int n = strlen(history), m = strlen(add) + 1;
    if (n + m > HISTORY) { /* drop from the front to make room */
        memmove(history, history + (n + m - HISTORY), HISTORY - m + 1);
        n = strlen(history);
    }
    if (n) strcat(history, " ");
    strcat(history, add);
}

/* The electrode drawn at a screen row and column: the panel turned 180 degrees. */
static int at(int row, int col) { return COLS * (ROWS - 1 - row) + (COLS - 1 - col); }

/* Draws the centroid over the grid. The cells are CELL_W + 1 characters apart across
 * and 4 lines apart down, so a centroid of (row, col) in cell units lands on the
 * middle line and middle character of that cell, and between cells in between. */
static void centroid(const int change[MPR121_ELECTRODES])
{
    float sum = 0, row = 0, col = 0;
    for (int r = 0; r < ROWS; r++)
        for (int c = 0; c < COLS; c++) {
            int w = change[at(r, c)] - NOISE;
            if (w <= 0) continue;
            sum += w;
            row += w * r;
            col += w * c;
        }
    if (sum == 0) return;
    int y = TOP + 1 + (int)lroundf(row / sum * 4);
    int x = 1 + CELL_W / 2 + (int)lroundf(col / sum * (CELL_W + 1));
    printf("\033[%d;%dH\033[1;38;5;196;48;5;231m\u25CF\033[0m", y, x);
}

static void draw(const uint16_t r[MPR121_ELECTRODES], const int change[MPR121_ELECTRODES], esp_err_t err,
                 int banner, int tok)
{
    printf("\033[H"); /* cursor home: draw over the previous frame */
    printf("MPR121, panel seen from the front, turned 180 degrees. Change from background, raw reading below.\033[K\n");
    printf("Background time constant %.0f s. Grey is under %d, red is %d or more. The red dot is the centroid. b restarts the background.\033[K\n\n",
           BACKGROUND_S, NOISE + 1, FULL_SCALE);
    if (err != ESP_OK) {
        printf("\033[0mno answer from the MPR121: %s\033[K\n\033[J", esp_err_to_name(err));
        fflush(stdout);
        return;
    }
    for (int row = 0; row < ROWS; row++) {
        for (int line = 0; line < 3; line++) {
            for (int col = 0; col < COLS; col++) {
                int e = at(row, col);
                colour(change[e]);
                if (line == 0)
                    printf(" ELE%-*d", CELL_W - 4, e);
                else if (line == 1)
                    printf("   %+*d    ", CELL_W - 7, change[e]);
                else
                    printf(" raw %-*d", CELL_W - 5, r[e]);
                printf("\033[0m ");
            }
            printf("\033[K\n");
        }
        printf("\033[K\n");
    }
    static const char *runs[] = {"", "2", "2 1", "2 1 0", "2 1 0 1", "2 1 0 1 2"};
    printf("Gesture 2+1+0+1+2+: matched [%s]\033[K\n", runs[gesture_progress()]);
    if (tok >= 0)
        printf("Pad under the dot: ELE%d\033[K\n", tok);
    else
        printf("Pad under the dot: %s\033[K\n", tok == -1 ? "between pads" : "no hand");
    printf("Recent: %s\033[K\n", history);
    const char *ip = wifi_address();
    if (ip)
        printf("Wi-Fi: on %s at %s\033[K\n", wifi_ssid(), ip);
    else
        printf("Wi-Fi: joining %s\033[K\n", wifi_ssid());
    printf("%s\033[K\n", kasa_status());
    printf("Bluetooth: \"%s\", %s\033[K\n", BLE_NAME, ble_state());
    if (banner > 0)
        printf("\033[1;38;5;16;48;5;46m  GESTURE: 2 > 1 > 0 > 1 > 2  \033[0m\033[K\n");
    printf("\033[J");
    centroid(change);
    fflush(stdout);
}

void app_main(void)
{
    /* The driver lets the console be read without blocking. */
    usb_serial_jtag_driver_config_t usb = USB_SERIAL_JTAG_DRIVER_CONFIG_DEFAULT();
    usb_serial_jtag_driver_install(&usb);
    usb_serial_jtag_vfs_use_driver();

    wifi_start();
    kasa_start();
    ble_start();
    printf("\033[2J\033[H\033[?25l"); /* clear the screen and hide the cursor */
    esp_err_t err;
    while ((err = mpr121_init()) != ESP_OK) {
        printf("\033[Hno answer from the MPR121 (%s), retrying\033[K\n", esp_err_to_name(err));
        fflush(stdout);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
    printf("\033[Htaking a baseline, keep hands away\033[K\n");
    fflush(stdout);
    take_baseline();
    printf("\033[2J");

    uint16_t r[MPR121_ELECTRODES];
    int change[MPR121_ELECTRODES];
    bool stream = false;
    int frame = 0, banner = 0;
    TickType_t wake = xTaskGetTickCount();
    for (;;) {
        char c = 0;
        usb_serial_jtag_read_bytes(&c, 1, 0);
        if (c == 'b') take_baseline();
        if (c == 't') kasa_toggle(); /* toggles the light by hand, for testing */
        if (c == 'r') stream = true;
        if (c == 'g') {
            stream = false;
            printf("\033[2J");
        }
        err = mpr121_read(r);
        bool fired = false;
        int tok = -2;
        if (err == ESP_OK) {
            filter(r, change);
            float row, col;
            bool dot = panel_centroid(change, &row, &col);
            tok = token(dot, row, col);
            if (dot) ble_report((col + 0.5f) * CELL_W_IN, (row + 0.5f) * CELL_H_IN, tok);
            remember(tok);
            fired = gesture_update(tok, PERIOD_MS);
        }
        if (fired) {
            banner = BANNER_FRAMES;
            if (!stream) kasa_toggle();
        }
        if (stream) {
            printf("C,%d", frame);
            for (int e = 0; e < MPR121_ELECTRODES; e++) printf(",%d", change[e]);
            printf(",%d,%d\n", tok, fired);
            fflush(stdout);
        } else {
            draw(r, change, err, banner, tok);
        }
        frame++;
        if (banner > 0) banner--;
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(PERIOD_MS));
    }
}
