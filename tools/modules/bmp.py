import struct
import math
from utils import read_in_chunks

HEADERSIZE = 0x76

def write_file(data, width, height, bitdepth, output):
    try:
        bmp = open(output, 'wb')
    except IOError as e:
        print(e, file = stderr)
        return 2

    datasize = int(width * height * bitdepth / 8)
    bmp.write(struct.pack('{}s'.format(2), b'BM'))
    bmp.write(struct.pack('<I', datasize + HEADERSIZE))
    bmp.write(struct.pack('I', 0x0))
    bmp.write(struct.pack('<I', HEADERSIZE))
    bmp.write(struct.pack('<I', 0x28))
    bmp.write(struct.pack('<I', width))
    bmp.write(struct.pack('<I', height))
    bmp.write(struct.pack('<H', 0x01))
    bmp.write(struct.pack('<H', 0x4))
    bmp.write(struct.pack('I', 0x0))
    bmp.write(struct.pack('<I', datasize))
    bmp.write(struct.pack('{}I'.format(2), 0x0, 0x0))
    bmp.write(struct.pack('<I', 0x10))
    bmp.write(struct.pack('I', 0x0))

    for piece in read_in_chunks(data, size = datasize + math.pow(2, bitdepth) * 4):
        bmp.write(piece)

    bmp.close()
