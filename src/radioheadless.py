import sounddevice as sd
import asyncio
import numpy as np
import sys
import os
import shutil

SAMPLE_RATE = 44100
BUFFER_SIZE = 4410 # 10 ms per bufffer
RINGLEN = 2048

class Frame():
    def __init__(self):
        self.power = 0.0
        self.buffer = np.empty((BUFFER_SIZE, 1), dtype=np.int16)
        self.reset()
    
    def reset(self):
        self.pos = 0
        self.valid = False

    def process(self, sample):
        self.buffer[self.pos] = sample
        self.pos += 1
        if self.pos == self.buffer.shape[0]:
            self.valid = True
            self.power = 0.0
            for i in range(self.buffer.shape[0]):
                s = self.buffer[i]
                print(f'sample[{i}]: {s}')
                self.power += self.buffer[i] * self.buffer[i]
            self.pos = 0
            self.valid = True
            print(f'power: {self.power}')
            return True
        return False

class RingBuffer():
    def __init__(self, length):
        self.ringbuf = []
        for i in range(length):
            self.ringbuf.append(Frame())
        self.ringstart = 0
        self.ringend = 0

    def detect(self):
        pass

async def collect(dev_id, dir):
    ringbuf = RingBuffer(RINGLEN)
    running = True
    no_recording = 0
    no_frames = 0
    loop = asyncio.get_event_loop()
    event = asyncio.Event()

    def callback(indata, frames, time, status):
        nonlocal ringbuf
        nonlocal running
        nonlocal no_recording
        nonlocal no_frames

        print(f'status: {status}, frames: {frames}, time: {time}, indata: {indata.shape}')
        buf = ringbuf.ringbuf[ringbuf.ringend]
        for i in range(indata.shape[0]):
            if buf.process(indata[i]):
                ringbuf.ringend = (ringbuf.ringend + 1) % RINGLEN
                if ringbuf.ringend == ringbuf.ringstart:
                    raise Exception('ring buffer overflow')
                # DEBUG
                sys.exit(-1)

        if no_frames > 1000 or not running:
            loop.call_soon_threadsafe(event.set)
            raise sd.CallbackStop
        no_frames += 1
        print(no_frames)

    try:
        stream = sd.InputStream(samplerate=SAMPLE_RATE, device=dev_id, channels=1, callback=callback)
        stream.start()
        await event.wait()
    except KeyboardInterrupt:
        running = False
    except asyncio.exceptions.CancelledError:
        pass
    finally:
        print('terminating')
        stream.stop()
        stream.close()

    return no_recording


def prepare_dir(dir):
    # DEBUG: remove directory if it exists
    shutil.rmtree(dir, ignore_errors=True)
    if os.path.exists(dir):
        raise Exception(f'directory {dir} already exists')
    os.makedirs(dir)

def usage():
    print(f"Usage: {sys.argv[0]} <dev_id> <directory>")
    print("Process audio from device <dev_is> into files in <directory>")
    print("<directory> is created and must not exist")
    devlist = sd.query_devices()
    print('Available devices:')
    for i in range(len(devlist)):
        dev = devlist[i] 
        print(f"{i}:  {dev['name']}")
    sys.exit(1)

async def main():
    if len(sys.argv) != 3:
        usage()

    devlist = sd.query_devices()
    dev_id = int(sys.argv[1])
    print(sd.default.device)
    sd.default.device = dev_id # devlist[dev_id]['name']
    print(sd.default.device)
    #usage()
    dir = sys.argv[2]
    prepare_dir(dir)
    recorded_audio = await collect(dev_id, dir)
    print(f"number of frames recorded: {recorded_audio}")

if __name__ == "__main__":
    asyncio.run(main())
