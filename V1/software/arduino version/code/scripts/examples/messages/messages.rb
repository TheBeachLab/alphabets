require 'serialport'

port_str = `ls /dev/tty.usbmodem*`.chomp
initial_message = ARGV[0]

# do not edit below this line
baud_rate = 9600
data_bits = 8
stop_bits = 1
parity = SerialPort::NONE
sp = SerialPort.new(port_str, baud_rate, data_bits, stop_bits, parity)

def write(sp,word = '')
  word = word.chomp.ljust(4)
  sp.write("#{word}\n")
end

write(sp, initial_message)
write(sp)
sleep(3)

while true
  File.readlines('messages.txt').each do |w|
    s = ""
    write(sp,w)
    while true
      while (i = sp.gets.chomp) do
        s += i
        break if s == "!!"
      end
      break
    end
    sleep(3)
  end
end
