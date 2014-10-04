#include <AccelStepper.h>

boolean calibrated = false;

// Steppers 1, 2 and 4 on big easy driver, stepper 3 on easydriver

String s0 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.:e ";
String s1 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.:e ";
String s2 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.:e ";
String s3 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.:e ";

AccelStepper stepper0(1,12,13);
AccelStepper stepper1(1,10,11);
AccelStepper stepper2(1,6,7);
AccelStepper stepper3(1,8,9);

char serialdata[4];
int lf = 10;

void setup()
{  
  Serial.begin(9600);
  Keyboard.begin();
  while (!Serial) {
    ; // wait for serial port to connect. Needed for Leonardo only
  }

  Serial.println("Flip-Flap Ready!");
  Serial.println("Enter the 4 characters that the flipflap is displaying:");
  
  stepper0.setMaxSpeed(12000);
  stepper0.setAcceleration(24000.0);
  stepper1.setMaxSpeed(12000);
  stepper1.setAcceleration(24000.0);
  stepper2.setMaxSpeed(12000);
  stepper2.setAcceleration(24000.0);
  stepper3.setMaxSpeed(12000);
  stepper3.setAcceleration(24000.0);
}

void loop()
{  
  if (Serial.available() > 0) {

    Serial.readBytesUntil(lf, serialdata, 4);
    
    int p0 = s0.indexOf(0);
    int p1 = s1.indexOf(1);
    int p2 = s2.indexOf(2);
    int p3 = s3.indexOf(3);
    
    Serial.println(p0);
    Serial.println(p1);
    Serial.println(p2);
    Serial.println(p3);
    
    if (calibrated) {
      // read incoming serial data:
      if (p0 >= 0) {
        stepper0.runToNewPosition(480 * p0);
        stepper0.setCurrentPosition(0);
        s0 = s0.substring(p0) + s0.substring(0,p0);
      }
      if (p1 >= 0) {
        stepper1.runToNewPosition(480 * p1);
        stepper1.setCurrentPosition(0);
        s1 = s1.substring(p1) + s1.substring(0,p1);
      }
      if (p2 >= 0) {
        stepper2.runToNewPosition(480 * p2);
        stepper2.setCurrentPosition(0);
        s2 = s2.substring(p2) + s2.substring(0,p2);
      }
      if (p3 >= 0) {
        stepper3.runToNewPosition(480 * p3);
        stepper3.setCurrentPosition(0);
        s3 = s3.substring(p3) + s3.substring(0,p3);
      }
    } else {
      s0 = s0.substring(p0) + s0.substring(0,p0);
      s1 = s1.substring(p1) + s1.substring(0,p1);
      s2 = s2.substring(p2) + s2.substring(0,p2);
      s3 = s3.substring(p2) + s3.substring(0,p3);
      calibrated = true;
    }

  }  

}

