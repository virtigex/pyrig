import sounddevice as sd
import asyncio
import numpy as np
import sys

DIR = 'C:\\Users\\Steve\\Documents\\radioheadless'
SAMPLE_RATE = 8000
BUFFER_SIZE = 80 # 10 ms per bufffer
RECLEN = 300 * 80 # five minutes

class Frame:
    def __init__(self):
        self.data = np.empty((BUFFER_SIZE, 1), dtype=np.int16)
        self.pos = 0
        self.valid = False

    def reset(self):
        self.pos = 0
        self.power = 0.0
        self.valid = False

    def fill(self, indata, offset):
        insamps = indata.shape[0] - offset
        towrite = BUFFER_SIZE - self.pos
        if insamps < towrite:
            for i in range(insamps):
                self.data[self.pos] = indata[offset + i]
                self.pos += 1
            return offset + insamps
        for i in range(towrite):
            self.data[self.pos] = indata[offset + i]
            self.pos += 1
        power = 0
        for s in self.data:
            samp = float(s)
            power += samp * samp
        self.power = power
        self.valid = True
        return offset + towrite

    def isvalid(self):
        return self.valid

class RingBuffer:

    def __init__(self, noframes):
        self.bufs = [Frame() for _ in range(noframes)]
        self.next = 0
        self.tail = 0

    def process(self, indata):
        offset = 0
        while offset < indata.shape[0]:
            bin = self.next % len(self.bufs)
            offset = self.bufs[bin].fill(indata, offset)
            if self.bufs[bin].isvalid():
                self.next += 1
                # bins self.tail to (self.next-1) are valid here
                self.detect()
                print(f'valid buf {bin}')
                bufsize = len(self.bufs)
                if (self.next % bufsize) == (self.tail % bufsize):
                    self.bufs[self.tail].reset()
                    self.tail += 1

    def detect(self):
        p = [self.bufs[(self.next-i-1) % len(self.bufs)].power for i in range(self.next - self.tail)]
        print(f'{len(p)}: {p}')

async def collect(dir):

    last_frame = None
    frame_last = np.empty((BUFFER_SIZE, 1), dtype=np.int16)
    running = True
    no_recording = 0
    no_frames = 0
    loop = asyncio.get_event_loop()
    event = asyncio.Event()
    ringbuf = RingBuffer(RECLEN)

    def callback(indata, frames, time, status):
        nonlocal no_recording
        nonlocal no_frames
        nonlocal ringbuf
        nonlocal running
        print(f'status: {status}, frames: {frames}, time: {time}, indata: {indata.shape}')
        ringbuf.process(indata)
        #if not running:
        if no_frames > 1000 or not running:
            loop.call_soon_threadsafe(event.set)
            raise sd.CallbackStop
        no_frames += 1
        print(no_frames)

    try:
        stream = sd.InputStream(device=None, samplerate=SAMPLE_RATE, channels=1, callback=callback)
        stream.start()
        await event.wait()
    except KeyboardInterrupt:
        running = False
        await event.wait()
    except asyncio.exceptions.CancelledError:
        pass
    finally:
        stream.stop()
        stream.close()

    return no_recording

async def main():
    if len(sys.argv)!= 2:
        print(f"Usage: {sys.argv[0]} <directory>")
        sys.exit(1)
    dir = sys.argv[1]
    recorded_audio = await collect(dir)
    print(f"number of frames recorded: {recorded_audio}")

if __name__ == "__main__":
    asyncio.run(main())
