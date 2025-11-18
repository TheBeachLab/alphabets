// Alphabets New Spool
$fn = 50;

// Parameters
ncards    = 64;   // number of cards
sdiam     = 85;   // diameter of the spool mm
e         = 2.15; // acrylic thickness / extrude height mm
//kerf    = 0.23; // for Fablab UAE Universal Laser mm
kerf      = 0.1;  // for Full Spectrum Gen5 laser
motorside = 1;    // 1 for motor side, 0 for shaft
d         = 56;   // distance between spools mm
w         = 35;   // support width mm
tabw      = 6;    // tab width mm
make3d    = true; // false for 2D, true for 3D (extruded by e)

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
        circle(1.5);
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
module spacer_2d() {
    // supports
    //translate ([5+srad+w/2,0,0]) {
    translate([0, 74, 0]) {
        copy_mirror([0,1,0]) {
            copy_mirror([1,0,0]) {
                square(size = [w/2, d/2], center = false);
                translate([w/2 - tabw, d/2])
                    tab();
            }
        }
    }
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

// ---- what to render ----
// spool();
// spacer();
// or both:
spool();
