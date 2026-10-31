/* Spots the gesture 2+1+0+1+2+, in regular-expression notation, in the stream of pad
 * tokens: the pad under the centroid, once per frame. Frames with the centroid between
 * pads or with no hand are skipped, so lifting the hand at the turn does not break the
 * match, but GESTURE_GAP_MS of them in a row start the match over. */
#pragma once
#include <stdbool.h>

#define GESTURE_GAP_MS 1000 /* the lift at the turn was 0.2-0.8 s in recordings */

/* Takes one frame's token: a pad number, or negative for between pads or no hand.
 * Returns true on the frame the gesture completes. */
bool gesture_update(int token, int frame_ms);

/* How many of the pattern's five runs (2, 1, 0, 1, 2) have been matched so far. */
int gesture_progress(void);
