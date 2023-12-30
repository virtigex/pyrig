import sys
import glob
import serial
import time

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
        except (OSError, Exception):
            pass
    return result



def list_audio():
    import pyaudio
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if 'USB Audio CODEC' in dev['name']:
            index = dev['index']
            name = dev['name']
            print(f'device {index} name {name}')

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
def test_port(port):
    try:
        ser = serial.Serial(port, 9600, timeout=1)
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

if __name__ == '__main__':
    print('rig 1.0')
    ports = serial_ports()
    if len(sys.argv) == 1:
        print(f'Usage: rig <serial-port-index>')
        for i in range(len(ports)):
            name = ports[i]
            print(f'{i}: {name}') 
    else:
        portnum = int(sys.argv[1])
        test_port(ports[portnum])

exit(0)
