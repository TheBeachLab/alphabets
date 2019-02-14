// Alphabets New Spool
$fn=(50);

// Parameters
ncards=64; // number of cards
sdiam=85; // diameter of the spool mm
e=2; // 3d printed part thickness mm

// Variables
srad=sdiam/2;
angle=360/ncards; // angle of rotation

// define copy_mirror function
module copy_mirror(vec=[0,1,0])
{
    children();
    mirror(vec) children();
} 

// Define axis motor
module axismotor() {
intersection() {square(size = [3, 6], center = true); circle(2.5);}
}

// Define axis support
module axis() {
circle(1.5);
}

// define aro
module aro() {
difference(){
    difference() { circle(srad); circle(srad-5);}
    for (a=[0:angle:360]){
    rotate(a) 
    translate([srad-2.5,0,0]) circle(1.5);
    }
}
}

// CODE STARTS HERE

linear_extrude(height = e) {
union(){    
aro();
    difference() {
        intersection() {
            union() {
                translate ([srad,0,0]) aro();
                translate ([-srad,0,0])  aro();
                circle (6.5);
                }
            circle(srad-5);
        }

    axismotor();
    }
}    
}

translate ([sdiam+5,0,0])
        union() {
        linear_extrude(height = 5) {circle(1.5);}
        linear_extrude(height = e) {
        union(){    
        aro();
                intersection() {
                    union() {
                        translate ([srad,0,0]) aro();
                        translate ([-srad,0,0])  aro();
                        circle (6.5);
                        }
                    circle(srad-5);
                }

        }    
        }
    }
