#!/usr/bin/python
# Filename: ff.py
version = '1.0'

# SPLIT-FLAP DISPLAY CONTROL LANGUAGE

# Created by Francisco in Fab lab Sitges
# May 2014
# Released under MIT license http://opensource.org/licenses/MIT


import serial
import time
import os
import sys
import pyttsx

#
# init the TTS engine
#
engine = pyttsx.init()

#
# Parameters
#
port='/dev/tty.usbserial-A100RTDG' # serial communication port
baud=9600 # connection speed in baud
max_delay=.1 # seconds
accel_delay=.005 # seconds

#
# define serial communication
#
ser = serial.Serial()

#
# open serial port
#
def OpenSerial(port,baud):
    # Open serial port
    ser.baudrate = baud
    ser.port = port
    ser.open()
    if ser.isOpen==True:
        print'Flip-Flap: Serial communication opened'
    else:
        print'Flip-Flap: There was a problem while opening serial connection'

#
# close serial port
#
def CloseSerial():
    # CLose serial port
    ser.close()
    if ser.isClosed()==True:
        print'Flip-Flap: Serial communication closed'


#
# define clearscreen()
#
def clearscreen(numlines=100):
    #Clear the console.
    #numlines is an optional argument used only as a fall-back.
    #
    if os.name == "posix":
        # Unix/Linux/MacOS/BSD/etc
        os.system('clear')
    elif os.name in ("nt", "dos", "ce"):
        # DOS/Windows
        os.system('CLS')
    else:
        # Fallback for other operating systems.
        print '\n' * numlines
    if ser.isOpen()==True:
        print 'Welcome to Flip-Flap version '+ version
        print 'Created by Francisco Sanchez Arroyo. Fab Lab Sitges'
        print 'Type help() for help'
        print 'Serial connection open'
        print 'System Ready!'
        engine.say('Flip-flap System Ready.')
        engine.runAndWait()
    else: print 'No serial connection to Flip-Flap'
    
#
# define help()
#
def help():
        print '#####################################'
        print '#   Flip-Flap currently supports:   #'
        print '#####################################'
        print ''
        print '  help() # This help'
        print '  clearscreen() # Clears the console'
        print ''
        print '  Serial connection:'
        print '  ------------------'
        print '  OpenSerial(port,baud) # Opens serial connection'
        print '  CloseSerial() # Closes serial connection'
        print ''
       print '  exit() # Quit to shell'
        print '  ######################'

        

#        
# Init Flip-Flap
#
OpenSerial('/dev/tty.usbserial-A100RTDG',9600) # open serial connection       
clearscreen() # clear the screen


# End of ff.py