import sounddevice as sd
import asyncio
import numpy as np
import numba
import sys

DIR = 'C:\\Users\\Steve\\Documents\\radioheadless'
SAMPLE_RATE = 48000
BUFFER_SIZE = 480 # 10 ms per bufffer
RECLEN = 3000 # five minutes

from ringbuffer import RingBuffer, RingListener

@numba.jit
def minmax(x):
    maximum = x[0]
    minimum = x[0]
    for i in x[1:]:
        if i > maximum:
            maximum = i
        elif i < minimum:
            minimum = i
    return (minimum, maximum)

class Listener(RingListener):
    def __init__(self):
        RingListener.__init__(self)

    def detect(self, bufs, next, tail):
        p = [bufs[(tail+i) % len(bufs)].power for i in range(next - tail)]
        print(*minmax(p), sep=',')
        #print(*p, sep=',')
        #print(f'RH: {len(p)}: {p}')
        return tail

async def collect(dir):
    last_frame = None
    frame_last = np.empty((BUFFER_SIZE, 1), dtype=np.int16)
    running = True
    no_recording = 0
    no_frames = 0
    loop = asyncio.get_event_loop()
    event = asyncio.Event()
    listener = Listener()
    ringbuf = RingBuffer(RECLEN, BUFFER_SIZE, listener)

    def callback(indata, frames, time, status):
        nonlocal no_recording
        nonlocal no_frames
        nonlocal ringbuf
        nonlocal running
        #print(f'status: {status}, frames: {frames}, time: {time}, indata: {indata}')
        ringbuf.process(indata)
        #if not running:
        if no_frames > 1000 or not running:
            loop.call_soon_threadsafe(event.set)
            raise sd.CallbackStop
        no_frames += 1
        #print(no_frames)

    try:
        stream = sd.InputStream(device=None, channels=1, samplerate=48000.0, callback=callback)
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
    #if len(sys.argv)!= 2:
    #    print(f"Usage: {sys.argv[0]} <directory>")
    #    sys.exit(1)
    #dir = sys.argv[1]
    dir = '/tmp'
    recorded_audio = await collect(dir)
    print(f"number of frames recorded: {recorded_audio}")

if __name__ == "__main__":
    asyncio.run(main())
