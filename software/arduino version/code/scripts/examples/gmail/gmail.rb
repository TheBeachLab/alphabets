require 'serialport'
require 'gmail'

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

while true
  Gmail.new(ENV['user'],ENV['pass']) do |gmail|
    email_count = gmail.inbox.count(:unread).to_s
    write(sp,email_count)
    puts "#{ENV['user']} has #{email_count} unread emails"
  end
  sleep(5)
end
