#include "gesture.h"

static const int pattern[] = {2, 1, 0, 1, 2};
#define N (int)(sizeof pattern / sizeof pattern[0])

static int matched; /* runs of the pattern matched so far, 0 to N */
static int gap_ms;

bool gesture_update(int token, int frame_ms)
{
    if (token < 0) {
        gap_ms += frame_ms;
        if (gap_ms > GESTURE_GAP_MS) matched = 0;
        return false;
    }
    gap_ms = 0;
    /* The final run of 2s can also be the first run of the next gesture. */
    if (matched == N && token != pattern[N - 1]) matched = 1;
    if (matched > 0 && token == pattern[matched - 1]) return false; /* the run goes on */
    if (matched < N && token == pattern[matched]) {
        matched++;
        return matched == N;
    }
    matched = token == pattern[0] ? 1 : 0; /* off the pattern: start over, maybe here */
    return false;
}

int gesture_progress(void) { return matched; }
