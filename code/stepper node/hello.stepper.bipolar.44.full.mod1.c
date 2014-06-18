//
//
// hello.stepper.bipolar.44.full.mod1.c
//
// bipolar full stepping hello-world
//
// Neil Gershenfeld
// 11/21/12
//
// (c) Massachusetts Institute of Technology 2012
// Permission granted for experimental and personal use;
// license for commercial sale available from MIT.
//
// BY FRANCISCO MIXED WITH 
//
// hello.bus.45.c
//
// 9600 baud serial bus hello-world
//
// Neil Gershenfeld
// 11/24/10
//
// (c) Massachusetts Institute of Technology 2010
// Permission granted for experimental and personal use;
// license for commercial sale available from MIT.
//

#include <avr/io.h>
#include <util/delay.h>
// From Network
#include <avr/pgmspace.h>  // Needed for Putchar
#include <string.h>


#define output(directions,pin) (directions |= pin) // set port direction for output
// From Network
#define input(directions,pin) (directions &= (~pin)) // set port direction for input

#define set(port,pin) (port |= pin) // set port pin
#define clear(port,pin) (port &= (~pin)) // clear port pin
#define pin_test(pins,pin) (pins & pin) // test for port pin
#define bit_test(byte,bit) (byte & (1 << bit)) // test for bit set

#define bridge_port PORTA // H-bridge port
#define bridge_direction DDRA // H-bridge direction
#define A2 (1 << PA0) // H-bridge output pins
#define A1 (1 << PA1) // "
#define B2 (1 << PA3) // "
#define B1 (1 << PA4) // "
#define on_delay() _delay_us(50) // PWM on time was 25 Chris 50
#define off_delay() _delay_us(10) // PWM off time was 5 Chris 10
#define PWM_count 125 // number of PWM cycles was 100 Chris 200

// From Network
#define bit_delay_time 100 // bit delay for 9600 with overhead
#define bit_delay() _delay_us(bit_delay_time) // RS232 bit delay
#define half_bit_delay() _delay_us(bit_delay_time/2) // RS232 half bit delay
#define led_delay() _delay_ms(100) // LED flash delay

#define led_port PORTB
#define led_direction DDRB
#define led_pin (1 << PA6)

#define serial_port PORTB
#define serial_direction DDRB
#define serial_pins PINB
#define serial_pin_in (1 << PB2)
#define serial_pin_out (1 << PA7)


static uint8_t count;

//
// A+ B+ PWM pulse
//
void pulse_ApBp() {
  clear(bridge_port, A2);
  clear(bridge_port, B2);
  set(bridge_port, A1);
  set(bridge_port, B1);
   for (count = 0; count < PWM_count; ++count) {
      set(bridge_port, A1);
      set(bridge_port, B1);
      on_delay();
      clear(bridge_port, A1);
      clear(bridge_port, B1);
      off_delay();
      }
   }
//
// A+ B- PWM pulse
//
void pulse_ApBm() {
  clear(bridge_port, A2);
  clear(bridge_port, B1);
  set(bridge_port, A1);
  set(bridge_port, B2);
   for (count = 0; count < PWM_count; ++count) {
      set(bridge_port, A1);
      set(bridge_port, B2);
      on_delay();
      clear(bridge_port, A1);
      clear(bridge_port, B2);
      off_delay();
      }
   }
//
// A- B+ PWM pulse
//
void pulse_AmBp() {
  clear(bridge_port, A1);
  clear(bridge_port, B2);
  set(bridge_port, A2);
  set(bridge_port, B1);
   for (count = 0; count < PWM_count; ++count) {
      set(bridge_port, A2);
      set(bridge_port, B1);
      on_delay();
      clear(bridge_port, A2);
      clear(bridge_port, B1);
      off_delay();
      }
   }
//
// A- B- PWM pulse
//
void pulse_AmBm() {
  clear(bridge_port, A1);
  clear(bridge_port, B1);
  set(bridge_port, A2);
  set(bridge_port, B2);
   for (count = 0; count < PWM_count; ++count) {
      set(bridge_port, A2);
      set(bridge_port, B2);
      on_delay();
      clear(bridge_port, A2);
      clear(bridge_port, B2);
      off_delay();
      }
   }
//
// clockwise step
//
void step_cw() {
   pulse_ApBp();
   pulse_AmBp();
   pulse_AmBm();
   pulse_ApBm();
   }
//
// counter-clockwise step
//
void step_ccw() {
   pulse_ApBm();
   pulse_AmBm();
   pulse_AmBp();
   pulse_ApBp();
   }

// FROM NETWORK

void get_char(volatile unsigned char *pins, unsigned char pin, char *rxbyte) {
  //
  // read character into rxbyte on pins pin
  //    assumes line driver (inverts bits)
  //
  *rxbyte = 0;
  while (pin_test(*pins,pin))
     //
     // wait for start bit
     //
     ;
  //
  // delay to middle of first data bit
  //
  half_bit_delay();
  bit_delay();
  //
  // unrolled loop to read data bits
  //
  if pin_test(*pins,pin)
     *rxbyte |= (1 << 0);
  else
     *rxbyte |= (0 << 0);
  bit_delay();
  if pin_test(*pins,pin)
     *rxbyte |= (1 << 1);
  else
     *rxbyte |= (0 << 1);
  bit_delay();
  if pin_test(*pins,pin)
     *rxbyte |= (1 << 2);
  else
     *rxbyte |= (0 << 2);
  bit_delay();
  if pin_test(*pins,pin)
     *rxbyte |= (1 << 3);
  else
     *rxbyte |= (0 << 3);
  bit_delay();
  if pin_test(*pins,pin)
     *rxbyte |= (1 << 4);
  else
     *rxbyte |= (0 << 4);
  bit_delay();
  if pin_test(*pins,pin)
     *rxbyte |= (1 << 5);
  else
     *rxbyte |= (0 << 5);
  bit_delay();
  if pin_test(*pins,pin)
     *rxbyte |= (1 << 6);
  else
     *rxbyte |= (0 << 6);
  bit_delay();
  if pin_test(*pins,pin)
     *rxbyte |= (1 << 7);
  else
     *rxbyte |= (0 << 7);
  //
  // wait for stop bit
  //
  bit_delay();
  half_bit_delay();
  }

void put_char(volatile unsigned char *port, unsigned char pin, char txchar) {
  //
  // send character in txchar on port pin
  //    assumes line driver (inverts bits)
  //
  // start bit
  //
  clear(*port,pin);
  bit_delay();
  //
  // unrolled loop to write data bits
  //
  if bit_test(txchar,0)
     set(*port,pin);
  else
     clear(*port,pin);
  bit_delay();
  if bit_test(txchar,1)
     set(*port,pin);
  else
     clear(*port,pin);
  bit_delay();
  if bit_test(txchar,2)
     set(*port,pin);
  else
     clear(*port,pin);
  bit_delay();
  if bit_test(txchar,3)
     set(*port,pin);
  else
     clear(*port,pin);
  bit_delay();
  if bit_test(txchar,4)
     set(*port,pin);
  else
     clear(*port,pin);
  bit_delay();
  if bit_test(txchar,5)
     set(*port,pin);
  else
     clear(*port,pin);
  bit_delay();
  if bit_test(txchar,6)
     set(*port,pin);
  else
     clear(*port,pin);
  bit_delay();
  if bit_test(txchar,7)
     set(*port,pin);
  else
     clear(*port,pin);
  bit_delay();
  //
  // stop bit
  //
  set(*port,pin);
  bit_delay();
  //
  // char delay
  //
  bit_delay();
  }

void put_string(volatile unsigned char *port, unsigned char pin, PGM_P str) {
  //
  // send character in txchar on port pin
  //    assumes line driver (inverts bits)
  //
  static char chr;
  static int index;
  index = 0;
  do {
     chr = pgm_read_byte(&(str[index]));
     put_char(&serial_port, serial_pin_out, chr);
     ++index;
     } while (chr != 0);
  }

void flash() {
  //
  // LED flash delay
  //
  clear(led_port, led_pin);
  led_delay();
  set(led_port, led_pin);
  }




int main(void) {
   //
   // main
   //
   // From Network
   static char chr;
   //
   // set clock divider to /1
   //
   CLKPR = (1 << CLKPCE);
   CLKPR = (0 << CLKPS3) | (0 << CLKPS2) | (0 << CLKPS1) | (0 << CLKPS0);
   //
   // initialize bridge pins
   //
   clear(bridge_port, A1);
   output(bridge_direction, A1);
   clear(bridge_port, A2);
   output(bridge_direction, A2);
   clear(bridge_port, B1);
   output(bridge_direction, B1);
   clear(bridge_port, B2);
   output(bridge_direction, B2);
   //
   // initialize output pins FROM NETWORK
   //
   set(serial_port, serial_pin_out);
   input(serial_direction, serial_pin_out);
   set(led_port, led_pin);
   output(led_direction, led_pin);
   //
   // main loop
   //
   while (1) {
   
    get_char(&serial_pins, serial_pin_in, &chr);
    if (chr == 40) {  // This is the '(' Character
		step_cw();}
		
	if (chr == 41) {  // This is the ')' Character
		step_ccw();}

	
	}
	
}
