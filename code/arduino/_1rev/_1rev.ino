#include <AccelStepper.h>

// Steppers 1, 2 and 4 on big easy driver, stepper 3 on easydriver


AccelStepper stepper1(1,12,13);
AccelStepper stepper2(1,10,11);
AccelStepper stepper3(1,6,7);
AccelStepper stepper4(1,8,9);
void setup()
{  
   Serial.begin(9600);
   Keyboard.begin();
   while (!Serial) {
    ; // wait for serial port to connect. Needed for Leonardo only
  }
  
  Serial.write("Flip-Flap Ready!");
   stepper1.setMaxSpeed(12000);
   stepper1.setAcceleration(24000.0);
   
   stepper2.setMaxSpeed(12000);
   stepper2.setAcceleration(12000.0);
   
   stepper3.setMaxSpeed(4000);
   stepper3.setAcceleration(3000.0);

   stepper4.setMaxSpeed(12000);
   stepper4.setAcceleration(12000.0);   
}
void loop()
{  
   if (Serial.available() > 0) {
    // read incoming serial data:
    char inChar = Serial.read();
    // Type the next ASCII value from what you received:
     switch (inChar){
     case 'a':
     stepper1.runToNewPosition(480);
     stepper1.setCurrentPosition(0);
     break;
     case 'b':
     stepper2.runToNewPosition(480);
     stepper2.setCurrentPosition(0);
     break;
     case 'c':
     stepper3.runToNewPosition(240);
     stepper3.setCurrentPosition(0);
     break;
     case 'd':
     stepper4.runToNewPosition(480);
     stepper4.setCurrentPosition(0);
     break;
     }
  }  
  
  
 //  stepper1.runToNewPosition(9600); //240 steps per letter
 //  stepper2.runToNewPosition(9600);
 //  stepper3.runToNewPosition(-4800); //120 steps per letter
 //  stepper4.runToNewPosition(9600);
 //  stepper1.setCurrentPosition(0);
 //  stepper2.setCurrentPosition(0);
 //  stepper3.setCurrentPosition(0);
 //  stepper4.setCurrentPosition(0);
 //  delay(2000);

}
