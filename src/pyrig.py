import sys
import glob
import serial
import sounddevice as sd
import soundfile as sf
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
    print(f'cmd: {cmd}')
    termcmd = cmd + ';\n'
    ser.write(termcmd.encode('utf-8'))
    res = ser.read(size=64)
    try:
        s = res.decode('utf-8')
        return s
    except UnicodeDecodeError as e:
        # kludge for rpis
        #print(cmd)
        #print(e)
        #print(res)
        return '?;'

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

        print('set power')
        cat_set_cmd(ser, 'EX139005') # 5W power
        res = cat_cmd(ser, 'EX139')
        print(res)

        # https://www.youtube.com/watch?v=CltsWx03UIo
        cat_set_cmd(ser, 'EX0321')      # CAT TOT 100ms
        cat_set_cmd(ser, 'EX0330')      # CAT RTS disable
        cat_set_cmd(ser, 'EX0621')      # DATA MODE other
        #cat_set_cmd(ser, 'EX064150')    # OTHER DISP (SSB) 1500ms
        #cat_set_cmd(ser, 'EX065150')    # OTHER DISP (SSB) 1500ms
        #cat_set_cmd(ser, 'EX06700')     # DATA LCUT FREQ off
        cat_set_cmd(ser, 'EX06800')     # DATA HCUT FREQ off
        cat_set_cmd(ser, 'EX0701')      # DATA IN SELECT rear
        cat_set_cmd(ser, 'EX0710')      # DATA PTT SELECT daky
        #cat_set_cmd(ser, 'EX0722')      # DATA PORT SELECT usb

        # NOTCH, CONT, DNR, DNF off
        cat_set_cmd(ser, 'BC00')        # NOTCH off

        # SHIFT 0Hz, WIDTH 3000ms
        # METER alc, PF PWR 15W, DT GAIN 18, IPO ipo

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

class PyRig:

    def __init__(self, serport, audport):
        print(f'rig_serial: {serport}')
        self.sounddev = audport
        #self.audin = sd.InputStream(device=audport, channels=1, samplerate=16000, callback=audio_callback)
        #self.audout = sd.OutputStream(channels=1, samplerate=16000)
        self.ser = serial.Serial(serport, 38400, timeout=1)
        self.ser.close()
        self.ser.open()
        self.tx(False)
        self.initialize()

    def close(self):
        self.mic_usb(False) # set handset active
        self.tx(False)
        self.ser.close()
        #self.audin.close()
        #self.audout.close()
        self.ser = None

    def initialize(self):
        try:
            # print current VFO-A 
            res = cat_cmd(self.ser, 'FA')
            print(res)

            print('set power')
            cat_set_cmd(self.ser, 'EX139005') # 5W power
            res = cat_cmd(self.ser, 'EX139')
            print(res)

            # https://www.youtube.com/watch?v=CltsWx03UIo
            cat_set_cmd(self.ser, 'EX0321')      # CAT TOT 100ms
            cat_set_cmd(self.ser, 'EX0330')      # CAT RTS disable
            cat_set_cmd(self.ser, 'EX0621')      # DATA MODE other
            #cat_set_cmd(self.ser, 'EX064150')    # OTHER DISP (SSB) 1500ms
            #cat_set_cmd(self.ser, 'EX065150')    # OTHER DISP (SSB) 1500ms
            #cat_set_cmd(self.ser, 'EX06700')     # DATA LCUT FREQ off
            cat_set_cmd(self.ser, 'EX06800')     # DATA HCUT FREQ off
            cat_set_cmd(self.ser, 'EX0701')      # DATA IN SELECT rear
            cat_set_cmd(self.ser, 'EX0710')      # DATA PTT SELECT daky
            #cat_set_cmd(self.ser, 'EX0722')      # DATA PORT SELECT usb

            cat_set_cmd(self.ser, 'OS00') # simplex

            # NOTCH, CONT, DNR, DNF off
            #cat_set_cmd(self.ser, 'BC00')        # NOTCH off

            # SHIFT 0Hz, WIDTH 3000ms
            # METER alc, PF PWR 15W, DT GAIN 18, IPO ipo
        except serial.SerialException:
            print('exception!')
            return False
        except RadioException:
            print('protocol exception')
            return False

    def mode_fm(self):
        cat_set_cmd(self.ser, 'MD04')

    def mode_lsb(self):
        cat_set_cmd(self.ser, 'MD01')

    def mode_usb(self):
        cat_set_cmd(self.ser, 'MD02')

    def freq_vfoa(self, khz):
        cmd = f'FA{khz:05}000'
        cat_set_cmd(self.ser, cmd)

    def mic_usb(self, state):
        if state:
            cat_set_cmd(self.ser, 'EX0741') # rear mic
        else:
            cat_set_cmd(self.ser, 'EX0740') # handset

    def tx(self, on):
        cmd = 'TX1' if on else 'TX0'
        cat_set_cmd(self.ser, cmd)

    def play(self, wavefile):
        data, fs = sf.read(wavefile)
        self.tx(True)
        sd.play(data, fs, device=self.sounddev)
        sd.wait()
        self.tx(False)

    def test(self):
        try:
            print('transmit on')
            self.tx(True)
            time.sleep(2)
            print('transmit off')
            self.tx(False)
        except serial.SerialException:
            print('exception!')
            return False
        except RadioException:
            print('protocol exception')
            return False
        return True

def main():
    print('rig 1.0')
    ports = serial_ports()
    sounddevs = sd.query_devices()
    if len(sys.argv) != 3:
        print(f'Usage: rig <serial-port-index>')
        for i in range(len(ports)):
            name = ports[i]
            print(f'{i}: {name}')
        print('audio:')
        print(sounddevs)
        #list_audio()
    else:
        portnum = int(sys.argv[1])
        snddev = int(sys.argv[2])
        rig = PyRig(ports[portnum], snddev)
        rig.mode_fm()
        rig.freq_vfoa(146460)
        rig.mic_usb(True)
        try:
            rig.play('assets/kn6orm-call.mp3')
            print('test passed')
        except Exception as e:
            print(e)
            print('test failed')
        finally:
            rig.close()

if __name__ == '__main__':
    main()

exit(0)
