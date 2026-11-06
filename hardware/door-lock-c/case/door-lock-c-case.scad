// Door Lock Jaskier: wall-mounted case, base and lid, for the 80 x 64 mm door-lock-c board.
//
// Axes as the case hangs on the wall: x to the right, y up (door and RS485
// terminals at the bottom, power on the left), z out of the wall.
// Origin: the board's bottom-left corner at the wall (z = 0 is the back face).
// KiCad positions convert as x = x_kicad - 100, y = 164 - y_kicad (board at 100, 100).
//
//   openscad -D 'part="base"' -o stl/door-lock-c-case-base.stl door-lock-c-case.scad
//   openscad -D 'part="lid"'  -o stl/door-lock-c-case-lid.stl  door-lock-c-case.scad
//
// "base" and "lid" are in print orientation (base on its back, lid on its top face).
// "base_fit" and "lid_fit" are in assembled position, for case_fit.py.
// "assembly", "open" (no lid) and "exploded" show the board too (board_stl, from
// kicad-cli pcb export stl; without it a plain slab stands in).

part = "assembly";      // [base, lid, assembly, open, exploded, base_fit, lid_fit]
name = ["DOOR LOCK", "JASKIER"];   // engraved in the middle of the lid, top line first; [] for none
name_size = [5, 7];                // both lines come out 41 mm wide
label = "";             // per box, a smaller line under the name, e.g. "BACK DOOR"
board_stl = "";         // KiCad STL of the board, for the assembly views only

/* [Board] */
pcb_w = 80;
pcb_h = 64;
pcb_t = 1.6;
holes = [[3.5, 3.5], [76.5, 3.5], [3.5, 60.5], [76.5, 60.5]];  // M3

/* [Case] */
gap = 0.5;          // board edge to wall
wall = 2.0;
floor_t = 3.0;
standoff_h = 5.0;   // the through-hole pins reach 2.9 mm below the board
top_clear = 17.5;   // board top face to lid underside: the SuperMini in its socket reaches about 15.3 mm
lid_t = 2.0;
r_in = 0.5;         // inside corner radius: the board's corners are square, and r_in = gap keeps the full gap there
fit = 0.25;         // lid lip and blocks to the walls, per side
lip_t = 1.2;
lip_h = 2.0;

/* [Screws] */
pcb_screw_hole = 2.7;   // M3 x 8 machine screws cut their own thread; 4.0 for M3 heat-set inserts
standoff_d = 7.0;
wall_screw_d = 4.3;     // 3.5-4 mm countersunk screws
wall_screw_head = 8.4;  // 90 degree countersink, flush with the ear or floor
// ears on the side walls, flat on the wall: the case goes up assembled and closed
ear_y = [6, 58];        // hole heights, the same on both sides: 4 ears, two diagonal ones are enough
ear_t = 4.0;
ear_r = 6.0;            // half the ear width, and its rounding around the hole
ear_hole_off = 6.5;     // hole centre to the side wall, room for a screwdriver or bit holder
ear_fillet = 1.5;       // where the ear meets the wall
// optional floor holes under the board, for screwing the empty base to the wall first:
// [[20, 20], [60, 20], [20, 44], [60, 44]]
wall_screws = [];
lid_screw_clear = 3.4;  // through the side walls
lid_screw_pilot = 2.6;  // M3 x 8 into the lid blocks
lid_screw_y = 26;
lid_screw_dz = 9.5;     // above the board top face

/* [Openings] */
led = [30.6, 60.5];     // LED2 centre
led_hole = 3.0;
led_window = 0;         // > 0 closes the hole with a skin this thick (print the lid in a light colour)
wire_z0 = 1.0;          // cable windows, above the board top face; wire entries are at 3.3-5.4 mm
wire_z1 = 7.6;

$fn = 48;
e = 0.01;

// derived
in0 = [-gap, -gap];
in1 = [pcb_w + gap, pcb_h + gap];
out0 = in0 - [wall, wall];
out1 = in1 + [wall, wall];
r_out = r_in + wall;
pcb_z = floor_t + standoff_h;     // board bottom face
top_z = pcb_z + pcb_t;            // board top face
wall_top = top_z + top_clear;     // lid underside
box_h = wall_top + lid_t;
cs = (wall_screw_head - wall_screw_d) / 2;   // countersink depth
echo(str("FIT pcb_z=", pcb_z, " top_z=", top_z, " wall_top=", wall_top, " box_h=", box_h,
         " out_w=", out1[0] - out0[0], " out_h=", out1[1] - out0[1], " out_x0=", out0[0], " out_y0=", out0[1],
         " lid_screw_y=", lid_screw_y, " lid_screw_z=", top_z + lid_screw_dz,
         " wire_z0=", top_z + wire_z0, " wire_z1=", top_z + wire_z1));

// cable windows: [x0, x1] on the bottom wall, [y0, y1] on the left wall
bottom_windows = [
    [7.0, 22.5],    // J2, door A: pins at 9.5 .. 20.0
    [28.0, 43.5],   // J3, door B: pins at 30.5 .. 41.0
    [50.5, 73.0],   // J4, RS485: pins at 53.0 .. 70.5
];
left_windows = [[47.5, 56.0]];  // J1, power: pins at 50.0 and 53.5
drain = [46.0, 49.0];           // small slot at the floor, bottom wall

// lid blocks for the side screws, over free board strips (only low SMD parts under them)
blocks = [
    [in0[0] + fit, 7.5],        // left: x range
    [72.5, in1[0] - fit],       // right
];
block_y = [lid_screw_y - 6, lid_screw_y + 6];
block_z0 = top_z + 3.0;

// ---------------------------------------------------------------- helpers

module rrect(p0, p1, r, h, z = 0) {
    translate([0, 0, z]) linear_extrude(h)
        offset(r = r) offset(delta = -r)
            translate(p0) square(p1 - p0);
}

// 2D teardrop pointing to +y, for horizontal holes printed without support
module teardrop(d) {
    circle(d = d);
    rotate(45) square(d / 2);
}

// horizontal hole along x, tip up (+z) or down
module hole_x(d, len, up = true) {
    rotate([90, 0, 90]) linear_extrude(len, center = true)
        rotate(up ? 0 : 180) teardrop(d);
}

// ---------------------------------------------------------------- base

module base() {
    difference() {
        union() {
            difference() {
                rrect(out0, out1, r_out, wall_top);
                rrect(in0, in1, r_in, wall_top, floor_t);
            }
            for (h = holes) translate([h[0], h[1], floor_t - e])
                cylinder(d = standoff_d, h = standoff_h + e);
            ears();
        }
        // ear screws, countersunk from the front
        for (p = ear_holes()) translate([p[0], p[1], 0]) {
            translate([0, 0, -1]) cylinder(d = wall_screw_d, h = ear_t + 2);
            translate([0, 0, ear_t - cs]) cylinder(d1 = wall_screw_d, d2 = wall_screw_head, h = cs + e);
            translate([0, 0, ear_t]) cylinder(d = wall_screw_head, h = ear_fillet + 1);
        }
        // board screws: blind, 1 mm short of the back face
        for (h = holes) translate([h[0], h[1], 1.0])
            cylinder(d = pcb_screw_hole, h = pcb_z);
        // wall screws, countersunk from the inside
        for (p = wall_screws) translate([p[0], p[1], 0]) {
            translate([0, 0, -1]) cylinder(d = wall_screw_d, h = floor_t + 2);
            translate([0, 0, floor_t - cs]) cylinder(d1 = wall_screw_d, d2 = wall_screw_head, h = cs + e);
            translate([0, 0, floor_t]) cylinder(d = wall_screw_head, h = 1);
        }
        // cable windows
        for (w = bottom_windows)
            translate([w[0], out0[1] - 1, top_z + wire_z0])
                cube([w[1] - w[0], wall + 2, wire_z1 - wire_z0]);
        for (w = left_windows)
            translate([out0[0] - 1, w[0], top_z + wire_z0])
                cube([wall + 2, w[1] - w[0], wire_z1 - wire_z0]);
        // condensation drain at the floor
        translate([drain[0], out0[1] - 1, floor_t]) cube([drain[1] - drain[0], wall + 2, 2]);
        // lid screws through the side walls
        for (x = [out0[0] + wall / 2, in1[0] + wall / 2])
            translate([x, lid_screw_y, top_z + lid_screw_dz])
                hole_x(lid_screw_clear, wall + 2);
    }
}

// side wall outer face, outward direction and hole centre of each ear
function ear_sides() = [[out0[0], -1], [out1[0], 1]];
function ear_holes() = [for (s = ear_sides(), y = ear_y) [s[0] + s[1] * ear_hole_off, y]];

module ears() {
    for (s = ear_sides(), y = ear_y) {
        xw = s[0];
        d = s[1];
        // flat ear: the rounded end around the hole, its root 1 mm into the wall
        linear_extrude(ear_t) hull() {
            translate([xw + d * ear_hole_off, y]) circle(r = ear_r);
            translate([d < 0 ? xw : xw - 1, y - ear_r]) square([1, 2 * ear_r]);
        }
        // 45 degree fillet along the wall, on top of the ear
        translate([0, y + ear_r, 0]) rotate([90, 0, 0]) linear_extrude(2 * ear_r)
            polygon([[xw - d, ear_t - e], [xw + d * ear_fillet, ear_t - e], [xw - d, ear_t + ear_fillet + 1]]);
    }
}

// ---------------------------------------------------------------- lid (assembled position)

module lid() {
    difference() {
        union() {
            rrect(out0, out1, r_out, lid_t, wall_top);
            // alignment lip inside the walls, cut where the SuperMini's antenna end is close
            difference() {
                rrect(in0 + [fit, fit], in1 - [fit, fit], 1.5, lip_h + e, wall_top - lip_h);   // rounder than a printed inside corner
                rrect(in0 + [fit + lip_t, fit + lip_t], in1 - [fit + lip_t, fit + lip_t],
                      0.5, lip_h + 1, wall_top - lip_h - 0.5);
                translate([35.6, in1[1] - 3, wall_top - lip_h - 1]) cube([20, 4, lip_h + 1]);
            }
            // side screw blocks
            for (b = blocks)
                translate([b[0], block_y[0], block_z0])
                    cube([b[1] - b[0], block_y[1] - block_y[0], wall_top - block_z0 + e]);
            // LED light tube down to 1.8 mm above the LED
            translate([led[0], led[1], top_z + 3.5])
                cylinder(d = led_hole + 3, h = wall_top - top_z - 3.5 + e);
        }
        // side screw pilots, 7 mm deep from each wall
        translate([in0[0] + fit + 3.5 - e, lid_screw_y, top_z + lid_screw_dz])
            hole_x(lid_screw_pilot, 7, up = false);
        translate([in1[0] - fit - 3.5 + e, lid_screw_y, top_z + lid_screw_dz])
            hole_x(lid_screw_pilot, 7, up = false);
        // LED hole and tube bore
        translate([led[0], led[1], top_z + 3.5 - 1])
            cylinder(d = led_hole + 0.6, h = wall_top - top_z - 3.5 + 1);
        translate([led[0], led[1], wall_top - 1])
            cylinder(d = led_hole, h = led_window > 0 ? lid_t + 1 - led_window : lid_t + 2);
        // engraved labels, read from the front
        engrave() {
            for (w = [[14.75, "DOOR A"], [35.75, "DOOR B"], [61.75, "RS485"]])
                translate([w[0], -0.6]) label_text(w[1], 3.0);
            translate([2.0, 51.75]) rotate(90) label_text("12V", 3.0);
            for (i = [0 : 1 : len(name) - 1])
                translate([pcb_w / 2, name_y(i)]) label_text(name[i], name_size[i]);
            if (label != "") translate([pcb_w / 2, 18]) label_text(label, 4);
        }
    }
}

// baseline of name line i: the bottom line at y = 26, 3 mm between lines (cap height = size)
function name_y(i) = i >= len(name) - 1 ? 26 : name_y(i + 1) + name_size[i + 1] + 3;

module label_text(s, size) {
    text(s, size = size, font = "Liberation Sans:style=Bold", halign = "center", valign = "baseline");
}

module engrave(depth = 0.6) {
    translate([0, 0, box_h - depth]) linear_extrude(depth + 1) children();
}

// ---------------------------------------------------------------- board, for the views

module board() {
    if (board_stl != "")
        color("darkgreen") translate([-100, 164, pcb_z + pcb_t - 1.51]) import(board_stl);
    else {
        color("darkgreen") translate([0, 0, pcb_z]) cube([pcb_w, pcb_h, pcb_t]);
        color("limegreen") for (w = bottom_windows) translate([w[0] + 0.8, 1, top_z]) cube([w[1] - w[0] - 1.6, 7.5, 9.3]);
    }
    // SuperMini in its socket (not in the KiCad model)
    color("royalblue") translate([36.62, 41.3, top_z + 11.1]) cube([18, 22.52, 1.0]);
    color("silver") translate([41.12, 40.3, top_z + 12.1]) cube([9.0, 7.4, 3.2]);   // USB-C
}

// ---------------------------------------------------------------- output

if (part == "base" || part == "base_fit") color("lightgrey") base();
else if (part == "lid") color("gainsboro") translate([0, 0, box_h]) rotate([180, 0, 0]) lid();
else if (part == "lid_fit") color("gainsboro") lid();
else if (part == "open") {
    color("lightgrey") base();
    board();
}
else if (part == "exploded") {
    color("lightgrey") base();
    board();
    color("gainsboro") translate([0, 0, 30]) lid();
}
else {
    color("lightgrey") base();
    board();
    color("gainsboro") lid();
}
