require 'serialport'
port_str = '/dev/tty.usbmodem1421'
baud_rate = 9600
data_bits = 8
stop_bits = 1
parity = SerialPort::NONE
sp = SerialPort.new(port_str, baud_rate, data_bits, stop_bits, parity)

sp.write("ITS \n")
# sleep(2)
# sp.write("1234\n")

def write(sp,word)
	sp.write("#{word}\n")
end

while true
	sp.write('TICK')
	sleep(2.8)
	sp.write('TOCK')
	sleep(2.3)
	sp.write('ITS ')
	sleep(3)
	sp.write("#{Time.now.strftime('%H%M')}\n")
	sleep(6)
	sp.write('    ')
	sleep(2.5)
end

# # sp.write("    \n")
# # sleep(1)
# # write(sp, "    ")
# # sleep(4)

# while true
# 	['CIAO', 'ROMA', 'MAKE', 'YOUR', 'OWN ', 'FLIP', 'FLAP', ' OR ', 'BUY ', 'ONE ', 'BOX ', 'FOR ', 'JUST', 'e49 ', 'FROM', 'OUR ', 'WEB ', 'SITE', '    '].each do |w|
# 		s = ""
# 		write(sp,w)
# 		while true
# 			while (i = sp.gets.chomp) do
# 				s += i
# 				puts s
# 				break if s == "!!"
# 			end
# 			break
# 		end
		
# 		sleep(2)
# 	end
# end