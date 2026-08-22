// Alphabets New Spool
$fn = 50;

// Parameters
ncards    = 64;   // number of cards
sdiam     = 85;   // diameter of the spool mm
e         = 2.15; // acrylic thickness / extrude height mm
//kerf    = 0.23; // for Fablab UAE Universal Laser mm
kerf      = 0.1;  // for Full Spectrum Gen5 laser
motorside = 1;    // 1 for motor side, 0 for shaft
flap_width = 50;  // visible card body width mm
axial_clearance = 1; // total clearance between card body and drum sides mm
shaft_axis_radius = 1.7; // 3.4 mm clearance hole for an M3 screw axle
d         = flap_width + axial_clearance; // distance between drum sides mm
w         = 35;   // support width mm
tabw      = 6;    // tab width mm
make3d    = true; // false for 2D, true for 3D (extruded by e)
part      = "spool"; // spool, spacer, layout, or assembly

// Variables
srad  = sdiam/2;
angle = 360/ncards; // angle of rotation

// define copy_mirror
module copy_mirror(vec=[0,1,0]) {
    children();
    mirror(vec) children();
}

// Define axis
module axis() {
    if (motorside == 1)
        intersection() {
            square(size = [3 - kerf, 6], center = true);
            circle(2.5);
        }
    else
        circle(shaft_axis_radius);
}

// define slots
module slots() {
    copy_mirror([0,1,0])
        copy_mirror([1,0,0])
            translate([w/2 - tabw/2, 20, 0])
                square(size = [tabw - (2*kerf), e - (2*kerf)], center = true);
}

// define tab
module tab() {
    square(size = [tabw, e], center = false);
}

// ---------------
// 2D spool shape
// ---------------
module spool_2d() {
    difference() {
        difference() {
            circle(srad);
            for (a = [0:angle:360]) {
                rotate(a)
                    translate([srad - 2.5, 0, 0])
                        circle(1.5);
            }
        }

        axis();
        slots();
    }
}

// ---------------
// 2D spacer shape
// ---------------
module spacer_profile_2d() {
    copy_mirror([0,1,0]) {
        copy_mirror([1,0,0]) {
            square(size = [w/2, d/2], center = false);
            translate([w/2 - tabw, d/2])
                tab();
        }
    }
}

module spacer_2d() {
    translate([0, 74, 0])
        spacer_profile_2d();
}

// ---------------
// Public modules: spool & spacer
// Automatically 2D or 3D depending on make3d
// ---------------
module spool() {
    if (make3d)
        linear_extrude(height = e)
            spool_2d();
    else
        spool_2d();
}

module spacer() {
    if (make3d)
        linear_extrude(height = e)
            spacer_2d();
    else
        spacer_2d();
}

module drum_assembly() {
    spool();
    translate([0, 0, e + d])
        spool();
    for (support_y = [-20, 20])
        translate([0, support_y, e + d/2])
            rotate([90, 0, 0])
                linear_extrude(height = e, center = true)
                    spacer_profile_2d();
}

// ---- what to render ----
assert(ncards == 64, "V2 drum requires 64 flap positions");
assert(d > flap_width, "drum must retain positive axial card clearance");

if (part == "spool")
    spool();
else if (part == "spacer")
    spacer();
else if (part == "layout") {
    spool();
    spacer();
}
else if (part == "assembly") {
    assert(make3d, "assembly requires make3d=true");
    drum_assembly();
}
else
    assert(false, "part must be spool, spacer, layout, or assembly");
