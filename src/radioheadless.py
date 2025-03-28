import sounddevice as sd
import asyncio
import numpy as np
import queue
import mp3
import time
import sys
import os

DIR = 'C:\\Users\\Steve\\Documents\\radioheadless'
SAMPLE_RATE = 48000
BUFFER_SIZE = 480 # 10 ms per bufffer
RECLEN = 3000 # five minutes
THRESH_UP = 2.5 # power
THRESH_DOWN = 1.0
COLLAR = 20
SCALE = 32000.0

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
        thresh_up = minpow + THRESH_UP
        thresh_down = minpow + THRESH_DOWN
        silence_start = 0
        for frameno in range(length):
            frame_id = tail + frameno
            buf_id = frame_id % ringlen
            power = bufs[buf_id].power
            if silence:
                if power > thresh_up:
                    silence = False
                    silence_start = frame_id
            else:
                if power < thresh_down:
                    silence = True
                    rec_start = silence_start - COLLAR
                    rec_end = frame_id + COLLAR
                    if rec_start >= tail and rec_end < next:
                        #print(rec_start, rec_end)
                        samps = []
                        pows = []
                        for i in range(rec_end - rec_start):
                            samps.append(bufs[rec_start+i].data)
                            pows.append(bufs[rec_start+i].power)
                        samples = np.concatenate(samps)
                        #print(f'shape {samples.shape}')
                        print(*pows, sep=",")
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

async def encoder(dir):
    waves_processed = 0
    while True:
        try:
            samples = await q.get()
            date = time.strftime('wave-%Y_%m_%d-%X.mp3')
            print(f'encoder got {samples.shape} at {date}')
            #mp3.encode(samples, dir, waves_processed)
            q.task_done()
            waves_processed += 1
        except Exception as e:
            print(f'encoder exception {e}')
            break
    return waves_processed
    
async def main():
    #if len(sys.argv)!= 2:
    #    print(f"Usage: {sys.argv[0]} <directory>")
    #    sys.exit(1)
    #dir = sys.argv[1]
    dir = 'c:\\tmp'
    task_encoder = asyncio.create_task(encoder(dir))
    task_collect = asyncio.create_task(collect(dir))
    results = await asyncio.gather(task_encoder, task_collect)
    print(results)
    recorded_audio = await collect(dir)
    print(f"number of frames recorded: {recorded_audio}")

if __name__ == "__main__":
    asyncio.run(main())
