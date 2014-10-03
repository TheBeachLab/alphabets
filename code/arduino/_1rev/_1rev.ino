#include <AccelStepper.h>

// Steppers 1, 2 and 4 on big easy driver, stepper 3 on easydriver

String s = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.:e ";

AccelStepper stepper1(1,12,13);
AccelStepper stepper2(1,10,11);
AccelStepper stepper3(1,6,7);
AccelStepper stepper4(1,8,9);

boolean calibrated = false;

char serialdata[4];
    int lf = 10;

void setup()
{  
   Serial.begin(9600);
   Keyboard.begin();
   while (!Serial) {
    ; // wait for serial port to connect. Needed for Leonardo only
  }
  
  Serial.write("Flip-Flap Ready!");
      Serial.println("Enter the 4 characters that the flipflap is displaying:");

   stepper1.setMaxSpeed(12000);
   stepper1.setAcceleration(24000.0);
   
   stepper2.setMaxSpeed(12000);
   stepper2.setAcceleration(24000.0);
   
   stepper3.setMaxSpeed(12000);
   stepper3.setAcceleration(24000.0);

   stepper4.setMaxSpeed(12000);
   stepper4.setAcceleration(24000.0);   
}
void loop()
{  
   if (Serial.available() > 0) {

    Serial.readBytesUntil(lf, serialdata, 4);
    
    char inChar = serialdata[3];
    int p = s.indexOf(inChar);

    if (calibrated) {
      // read incoming serial data:
      if (p >= 0) {
        stepper1.runToNewPosition(480 * p);
        stepper1.setCurrentPosition(0);
        s = s.substring(p) + s.substring(0,p);
      } else if (inChar == '`') {
        stepper1.runToNewPosition(480);
        stepper1.setCurrentPosition(0);
      }
    } else {
      s = s.substring(p) + s.substring(0,p);
      calibrated = true;
    }
    
  }  

}
