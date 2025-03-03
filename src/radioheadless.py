import sounddevice as sd
import asyncio
import numpy as np
import sys

DIR = 'C:\\Users\\Steve\\Documents\\radioheadless'
SAMPLE_RATE = 8000
BUFFER_SIZE = 80 # 10 ms per bufffer


async def collect(dir):

    last_frame = None
    frame_last = np.empty((BUFFER_SIZE, 1), dtype=np.int16)
    running = True
    no_recording = 0
    no_frames = 0
    loop = asyncio.get_event_loop()
    event = asyncio.Event()

    def callback(indata, frames, time, status):
        nonlocal no_recording
        nonlocal no_frames
        nonlocal running
        print(f'status: {status}, frames: {frames}, time: {time}, indata: {indata.shape}')
        #if not running:
        if no_frames > 1000 or not running:
            loop.call_soon_threadsafe(event.set)
            raise sd.CallbackStop
        no_frames += 1
        print(no_frames)

    try:
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback)
        await event.wait()
    except KeyboardInterrupt:
        running = False
    finally:
        stream.stop()
        stream.close()

    return no_recording

async def main():
    if len(sys.args) != 2:
        print(f"Usage: {sys.argv[0]} <directory>")
        sys.exit(1)
    dir = sys.argv[1]
    recorded_audio = await collect(dir)
    print(f"number of frames recorded: {recorded_audio}")

if __name__ == "__main__":
    asyncio.run(main())
