nc=6;
nr=2;
ms=70;
dm=30;

r1=20;
r2=5;
l1=80;
l2=2*r1;
l3=10;
kerf=0.2;
e=2.5;

module side(){
difference() {
union() {
circle(r1);
translate ([l1/2,0,0]) square([l1,l2],true);
translate ([l1,-l2/2,0]) square([e,l3]);
translate ([l1,l2/2-l3,0]) square([e,l3]);
}
circle(r2);
}
}

module inset()
{
square([e,l3]);

    }
    
inset();
    