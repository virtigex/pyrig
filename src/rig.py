import sys
import glob
import pyaudio
import serial
import time

print('rig 1.0')


def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


ports = serial_ports()

print(ports)

p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    dev = p.get_device_info_by_index(i)
    if 'USB Audio CODEC' in dev['name']:
        print(f'device {dev['index']} name {dev['name']}')

class RadioException(Exception):
    pass

def cat_cmd(ser, cmd):
    termcmd = cmd + ';\n'
    ser.write(termcmd.encode('utf-8'))
    res = ser.read(size=64)
    return res.decode('utf-8')


def cat_set_cmd(ser, cmd):
    result = cat_cmd(ser, cmd)
    if result != '?;':
        raise RadioException('no reply')

try:
    ser = serial.Serial(ports[0], 9600, timeout=1)
    ser.close()
    ser.open()
except serial.SerialException:
    print('cannot open serial device')
    exit(-1)

try:
    cat_set_cmd(ser, 'FA028075000')
    cat_set_cmd(ser, 'MD02') # USB

    res = cat_cmd(ser, 'FA')
    print(res)

    print('transmitting')
    cat_set_cmd(ser, 'TX1')

    time.sleep(2)

    cat_set_cmd(ser, 'TX0')
    print('transmit finished')
except serial.SerialException:
    print('exception!')
except RadioException:
    print('protocol exception')

try:
    ser.close()
except serial.SerialException:
    print('exception!')

exit(0)
