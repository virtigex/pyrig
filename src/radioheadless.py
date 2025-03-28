import sounddevice as sd
import asyncio
import numpy as np
import queue

DIR = 'C:\\Users\\Steve\\Documents\\radioheadless'
SAMPLE_RATE = 48000
BUFFER_SIZE = 480 # 10 ms per bufffer
RECLEN = 3000 # five minutes
THRESH = 2.5 # power
COLLAR = 20

from ringbuffer import RingBuffer, RingListener

q = queue.Queue()

class Listener(RingListener):
    def __init__(self):
        RingListener.__init__(self)

    def detect(self, bufs, next, tail):
        #print(f'next {next}')
        ringlen = len(bufs)
        length = next - tail
        minpow = bufs[tail % ringlen].power
        for frameno in range(length):
            frame_id = tail + frameno
            buf_id = frame_id % ringlen
            if not bufs[buf_id].valid:
                raise Exception('buffer error')
            if minpow > bufs[buf_id].power:
                minpow = bufs[buf_id].power
        silence = True
        thresh = minpow + THRESH
        silence_start = 0
        for frameno in range(length):
            frame_id = tail + frameno
            buf_id = frame_id % ringlen
            power = bufs[buf_id].power
            if silence:
                if power > thresh:
                    silence = False
                    silence_start = frame_id
            else:
                if power < thresh:
                    silence = True
                    rec_start = silence_start - COLLAR
                    rec_end = frame_id + COLLAR
                    if rec_start >= tail and rec_end < next:
                        print(rec_start, rec_end)
                        samps = []
                        for i in range(rec_end - rec_start):
                            samps.append(bufs[rec_start+i].data)
                        samples = np.concatenate(samps)
                        print(f'shape {samples.shape}')
                        q.put(samples)

                        #print(f'tail set to {tail + frameno} next is {next}')
                        return tail + frameno
        #print(f'tail remaining at {tail}')
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
        nonlocal ringbuf
        nonlocal running
        #print(f'status: {status}, frames: {frames}, time: {time}, indata: {indata.shape}')
        ringbuf.process(indata)
        if not running:
            print(f'terminating5')
            loop.call_soon_threadsafe(event.set)
            raise sd.CallbackStop

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
