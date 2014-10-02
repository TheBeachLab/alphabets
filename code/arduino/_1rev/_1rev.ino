#include <AccelStepper.h>

AccelStepper stepper1(1,12,13);
AccelStepper stepper2(1,10,11);
AccelStepper stepper3(1,6,7);
AccelStepper stepper4(1,8,9);
void setup()
{  
   stepper1.setMaxSpeed(12000);
   stepper1.setAcceleration(12000.0);
   
   stepper2.setMaxSpeed(12000);
   stepper2.setAcceleration(12000.0);
   
   stepper3.setMaxSpeed(4000);
   stepper3.setAcceleration(3000.0);

   stepper4.setMaxSpeed(12000);
   stepper4.setAcceleration(12000.0);   
}
void loop()
{  
   stepper1.runToNewPosition(19200);
   stepper2.runToNewPosition(19200);
   stepper3.runToNewPosition(-9600);
   stepper4.runToNewPosition(19200);
   stepper1.setCurrentPosition(0);
   stepper2.setCurrentPosition(0);
   stepper3.setCurrentPosition(0);
   stepper4.setCurrentPosition(0);
   delay(2000);

}
