require 'serialport'

port_str = '/dev/tty.usbmodem1421'
initial_message = "ITS "

# do not edit below this line
baud_rate = 9600
data_bits = 8
stop_bits = 1
parity = SerialPort::NONE
sp = SerialPort.new(port_str, baud_rate, data_bits, stop_bits, parity)

def write(sp,word)
	sp.write("#{word}\n")
end

write(sp, initial_message)

while true
	write(sp,'TICK')
	sleep(2.8)
	write(sp,'TOCK')
	sleep(2.3)
	write(sp,'ITS ')
	sleep(3)
	write(sp,"#{Time.now.strftime('%H%M')}\n")
	sleep(6)
	write(sp,'    ')
	sleep(2.5)
end
