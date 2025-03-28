import numpy as np
import math

IOTA = 1.0e-09

class Frame:
    def __init__(self, framesize):
        self.framesize = framesize
        self.data = np.empty((self.framesize, 1), dtype=np.float32)
        self.pos = 0
        self.valid = False

    def reset(self):
        self.pos = 0
        self.power = 0.0
        self.valid = False

    def fill(self, indata, offset):
        insamps = indata.shape[0] - offset
        towrite = self.framesize - self.pos
        if insamps < towrite:
            for i in range(insamps):
                self.data[self.pos] = indata[offset + i][0]
                self.pos += 1
            return offset + insamps
        for i in range(towrite):
            self.data[self.pos] = indata[offset + i][0]
            self.pos += 1
        power = 0
        for s in self.data:
            samp = float(s)
            power += samp * samp
        if power < IOTA:
            power = IOTA
        self.power = math.log10(power)
        self.valid = True
        return offset + towrite

    def isvalid(self):
        return self.valid

class RingBuffer:

    def __init__(self, noframes, framesize, listener):
        self.bufs = [Frame(framesize) for _ in range(noframes)]
        self.listener = listener
        self.next = 0
        self.tail = 0

    def process(self, indata):
        offset = 0
        #print(f'shape = {indata.shape}')
        #print(indata)
        while offset < indata.shape[0]:
            bin = self.next % len(self.bufs)
            offset = self.bufs[bin].fill(indata, offset)
            if self.bufs[bin].isvalid():
                self.next += 1
                # bins self.tail to (self.next-1) are valid here
                self.tail = self.listener.detect(self.bufs, self.next, self.tail)
                #print(f'valid buf {bin}')
                bufsize = len(self.bufs)
                if (self.next % bufsize) == (self.tail % bufsize):
                    self.bufs[self.tail % bufsize].reset()
                    self.tail += 1

class RingListener:
    def __init__(self):
        pass

    def detect(self, bufs, next, tail):
        p = [bufs[(next-i-1) % len(bufs)].power for i in range(next - tail)]
        print(f'{len(p)}: {p}')
        # tail does not move in dummy implemenation
        return self.tail
