// Tray for the touch panel: 12 copper-foil pads on top, their wires in channels on the
// underside, and shallow pockets for the MPR121 and the XIAO on a tab beside the
// bottom-right corner.
//
// Coordinates are seen from the front: x to the right, y up, z out of the panel toward
// the hand, with the origin at the bottom-left corner of the pad grid. The tray prints
// in four tiles because the panel is larger than the X2D's 256 mm bed. The seams fall
// in the gaps between pads and lock with glued dovetails. Every tile is also narrower
// than 235 mm, the width the X2D's right nozzle can reach, so either nozzle can print
// any tile.

/* [View] */
part = "assembly"; // [assembly, tile_bl, tile_br, tile_tl, tile_tr]

/* [Panel] */
inch = 25.4;
W = 12 * inch;          // pad grid width
H = 15 * inch;          // pad grid height
cols = 3;
rows = 4;
gap = 0.25 * inch;      // between neighbouring pads
t = 3;                  // plate thickness

/* [Pads and wires] */
pad_depth = 0.4;        // recess that locates each copper sticker
hole_d = 1.6;           // wire hole through the plate, inside each pad's corner
hole_inset = 6;         // hole centre from the pad's bottom-right corner, in x and y
groove_len = 10;        // top groove the stripped wire end lies in, under the sticker
groove_w = 1.0;
groove_d = 0.6;
chan_w = 2.5;           // underside channel from a column of pads
chan_d = 1.8;
trunk_w = 5;            // underside channel carrying all 12 wires to the MPR121
trunk_y = 4.5;          // its centre line

/* [Boards] */
tab_gap = 12;           // from the pad grid to the boards, to keep their ground off the pads
tab = [50, 50];         // the plate beside the bottom-right corner that carries the boards
pocket_depth = 1.2;     // a board sits in it and stands 0.4 mm proud
pocket_clear = 0.15;    // added around each board's outline
// Adafruit MPR121 STEMMA QT breakout, from Adafruit's Eagle file: 33.02 x 19.05 mm.
// Its electrode row (JP1, 13 pins at 2.54 mm, centred) is 17.78 mm from the edge with
// the power row (JP2, 7 pins). The board lies rotated so that the electrode row is
// nearest the bottom edge, over the trunk.
mpr = [33.02, 19.05];
mpr_at = [W + tab_gap + 1, 3.5];    // bottom-left corner of the board
mpr_row = 1.27;                     // electrode row from the board's bottom edge, as laid
// XIAO ESP32-C3, 21 x 17.5 mm, USB-C toward +x and overhanging the tab's edge so the
// plug can go in.
xiao = [21, 17.5];
xiao_at = [W + tab[0] - xiao[0] + 1, 28];

/* [Dovetails] */
dt_neck = 8;
dt_flare = 12;
dt_len = 6;
dt_clear = 0.12;        // taken off each side of a dovetail

$fn = 32;
eps = 0.01;

cw = W / cols;
ch = H / rows;
split_x = 2 * cw;       // tile seams, both in pad gaps
split_y = 2 * ch;

// Pad c (from the left, seen from the front) in row rb (from the bottom).
function pad_origin(c, rb) = [c * cw + gap / 2, rb * ch + gap / 2];
pad_size = [cw - gap, ch - gap];
function hole_at(c, rb) = pad_origin(c, rb) + [pad_size[0] - hole_inset, hole_inset];
// Electrodes count left to right and top to bottom, seen from the front.
function ele(c, rb) = 3 * (rows - 1 - rb) + c;

module plate()
{
    cube([W, H, t]);
    translate([W - eps, 0, 0]) cube([tab[0] + eps, tab[1], t]);
}

module board_pockets()
{
    for (b = [[mpr_at, mpr], [xiao_at, xiao]])
        translate([b[0][0] - pocket_clear, b[0][1] - pocket_clear, t - pocket_depth])
            cube([b[1][0] + 2 * pocket_clear, b[1][1] + 2 * pocket_clear, pocket_depth + 1]);
    // a slot through the plate under the electrode row, where the wires come up from the
    // trunk into the board's pads from below
    translate([mpr_at[0] + mpr[0] / 2 - 16, mpr_at[1] + mpr_row - 1.25, -1]) cube([32, 2.5, t + 2]);
}

module pad_cuts(c, rb)
{
    o = pad_origin(c, rb);
    h = hole_at(c, rb);
    translate([o[0], o[1], t - pad_depth]) cube([pad_size[0], pad_size[1], pad_depth + 1]);
    translate([h[0], h[1], -1]) cylinder(d = hole_d, h = t + 2);
    translate([h[0] - groove_len, h[1] - groove_w / 2, t - pad_depth - groove_d])
        cube([groove_len, groove_w, groove_d + eps]);
}

// The underside: one channel up each column through its four holes, and the trunk
// along the bottom edge to the slot under the MPR121's electrode row.
module wire_channels()
{
    for (c = [0 : cols - 1]) {
        hx = hole_at(c, 0)[0];
        top = hole_at(c, rows - 1)[1];
        translate([hx - chan_w / 2, trunk_y, -1]) cube([chan_w, top - trunk_y + chan_w / 2, chan_d + 1]);
    }
    x0 = hole_at(0, 0)[0] - chan_w / 2;
    x1 = mpr_at[0] + mpr[0] / 2 + 16;
    translate([x0, trunk_y - trunk_w / 2, -1]) cube([x1 - x0, trunk_w, chan_d + 1]);
}

// Electrode numbers engraved on the underside beside each hole, mirrored so that they
// read correctly from below, where the wiring is done.
module labels()
{
    for (c = [0 : cols - 1], rb = [0 : rows - 1]) {
        h = hole_at(c, rb);
        translate([h[0] - 6, h[1] + 4, -1])
            linear_extrude(1 + 0.4)
                mirror([1, 0]) text(str("ELE", ele(c, rb)), size = 4, halign = "left", valign = "bottom");
    }
}

module tray()
{
    difference() {
        plate();
        for (c = [0 : cols - 1], rb = [0 : rows - 1]) pad_cuts(c, rb);
        board_pockets();
        wire_channels();
        labels();
    }
}

// ---- splitting into tiles ----------------------------------------------------

// A dovetail at the seam, pointing +x, overlapping 1 mm back into the tile it belongs to.
module dovetail(shrink)
{
    offset(delta = -shrink)
        polygon([[-1, -dt_neck / 2], [0, -dt_neck / 2], [dt_len, -dt_flare / 2],
                 [dt_len, dt_flare / 2], [0, dt_neck / 2], [-1, dt_neck / 2]]);
}

big = 1000;
dt_along_x_seam = [50, 140, 240, 330];      // y positions of the dovetails on the x = split_x seam
dt_along_y_seam = [50, 150, 250];           // x positions on the y = split_y seam

// side 0 is the left (or bottom) tile, which carries the dovetails.
module x_side(side)
{
    if (side == 0)
        union() {
            translate([-big, -big]) square([split_x + big, 2 * big]);
            for (y = dt_along_x_seam) translate([split_x, y]) dovetail(dt_clear);
        }
    else
        difference() {
            translate([split_x, -big]) square([big, 2 * big]);
            for (y = dt_along_x_seam) translate([split_x, y]) dovetail(0);
        }
}

module y_side(side)
{
    if (side == 0)
        union() {
            translate([-big, -big]) square([2 * big, split_y + big]);
            for (x = dt_along_y_seam) translate([x, split_y]) rotate(90) dovetail(dt_clear);
        }
    else
        difference() {
            translate([-big, split_y]) square([2 * big, big]);
            for (x = dt_along_y_seam) translate([x, split_y]) rotate(90) dovetail(0);
        }
}

module tile(xs, ys)
{
    intersection() {
        tray();
        translate([0, 0, -5]) linear_extrude(t + 10) intersection() { x_side(xs); y_side(ys); }
    }
}

if (part == "assembly") tray();
if (part == "tile_bl") tile(0, 0);
if (part == "tile_br") tile(1, 0);
if (part == "tile_tl") tile(0, 1);
if (part == "tile_tr") tile(1, 1);
