// FLIP-FLAP
// Arduino code for Maker Faire Rome
// October 2014
// by John Rees

// Declare the display not calibrated
boolean calibrated = false;

// Declare array strings for the 4 units
String s0 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.:e ";
String s1 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.:e ";
String s2 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.:e ";
String s3 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.:e ";

// Define pin numbers
int STEP_0 = 8;
int STEP_1 = 6;
int STEP_2 = 10;
int STEP_3 = 12;

int DIR_0 = 9;
int DIR_1 = 7;
int DIR_2 = 11;
int DIR_3 = 13;



//int limit = 10000;
//int counter = 0;

char serialdata[4];

void setup() {
  
  // Init Serial
  Serial.begin(9600);
  Keyboard.begin();
  while (!Serial) {
    ; // wait for serial port to connect. Needed for Leonardo only
  }

  
  // Init stepper pins
  pinMode(DIR_3, OUTPUT);     
  pinMode(STEP_3, OUTPUT);
  digitalWrite(DIR_3, HIGH);
  digitalWrite(STEP_3, LOW);

  pinMode(DIR_2, OUTPUT);     
  pinMode(STEP_2, OUTPUT);
  digitalWrite(DIR_2, HIGH);
  digitalWrite(STEP_2, LOW);

  pinMode(DIR_0, OUTPUT);     
  pinMode(STEP_0, OUTPUT);
  digitalWrite(DIR_0, HIGH);
  digitalWrite(STEP_0, LOW);

  pinMode(DIR_1, OUTPUT);     
  pinMode(STEP_1, OUTPUT);
  digitalWrite(DIR_1, HIGH);
  digitalWrite(STEP_1, LOW);
  
  
  // Display Message
//  Serial.println("Flip-Flap Ready!");
//  Serial.println("Enter the 4 characters that the flipflap is displaying:");

}

int p0;
int p1;
int p2;
int p3;

void loop() {

  if (Serial.available() > 0) {

    Serial.readBytesUntil(10, serialdata, 4);
    p0 = s0.indexOf(serialdata[0]);
    p1 = s1.indexOf(serialdata[1]);
    p2 = s2.indexOf(serialdata[2]);
    p3 = s3.indexOf(serialdata[3]);
    
    if(!calibrated) {
      calibrated = true;
      s0 = s0.substring(p0) + s0.substring(0,p0);
      s1 = s1.substring(p1) + s1.substring(0,p1);
      s2 = s2.substring(p2) + s2.substring(0,p2);
      s3 = s3.substring(p3) + s3.substring(0,p3);

      p0 = s0.indexOf(' ');
      p1 = s1.indexOf(' ');
      p2 = s2.indexOf(' ');
      p3 = s3.indexOf(' ');
    }

      p0 *= 480;
      p1 *= 240;
      p2 *= 480;    
      p3 *= 480;
      
      
        
      // Obtaining max of p0,p1,p2,p3  
      int maxp=max(p0,p1);
      maxp=max(maxp,p2);
      maxp=max(maxp,p3);
 
      
      // Put all steps in the same common loop
      for(int i = 0; i < maxp; i++) {
        
        if (i < p0) {
          digitalWrite(STEP_0, HIGH);}
        if (i < p1) {
          digitalWrite(STEP_1, HIGH);}
        if (i < p2) {
          digitalWrite(STEP_2, HIGH);}
        if (i < p3)  {
          digitalWrite(STEP_3, HIGH);}
        
        delayMicroseconds(120);
        
        if (i < p0) {
          digitalWrite(STEP_0, LOW);}
        if (i < p1) {
          digitalWrite(STEP_1, LOW);}
        if (i < p2) {
          digitalWrite(STEP_2, LOW);}
        if (i < p3)  {
          digitalWrite(STEP_3, LOW);}    
      } 
      Serial.println('!');
      
      p0 /= 480;
      p1 /= 240;
      p2 /= 480;    
      p3 /= 480; 
      
      
     // Shift strings
     s0 = s0.substring(p0) + s0.substring(0,p0);
     s1 = s1.substring(p1) + s1.substring(0,p1);
     s2 = s2.substring(p2) + s2.substring(0,p2);
     s3 = s3.substring(p3) + s3.substring(0,p3);
     
     
     

  
      
//      
//     Serial.print(p0); 
//     Serial.print(">>"); 
//     Serial.println(s0); 
    
  }



}


