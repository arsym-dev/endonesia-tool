import struct
import math
from endotool.utils import read_in_chunks

HEADERSIZE = 0x36

def write_file(data, width, height, bitdepth, output, colorsize = 0):
    try:
        bmp = open(output, 'wb')
    except IOError as e:
        print(e, file = stderr)
        return 2

    palettesize = pow(2, bitdepth) * 4 if colorsize == 0 and bitdepth < 16 else colorsize * 4

    datasize = int(width * height * bitdepth / 8)
    bmp.write(struct.pack('2s', b'BM'))
    bmp.write(struct.pack('<I', palettesize + datasize + HEADERSIZE))
    bmp.write(struct.pack('I', 0x0))
    bmp.write(struct.pack('<I', HEADERSIZE))
    bmp.write(struct.pack('<I', 0x28))
    bmp.write(struct.pack('<I', width))
    bmp.write(struct.pack('<I', height))
    bmp.write(struct.pack('<H', 0x01))
    bmp.write(struct.pack('<H', bitdepth))
    bmp.write(struct.pack('<I', 0x0))
    bmp.write(struct.pack('<I', datasize))
    bmp.write(struct.pack('{}I'.format(2), 0x0, 0x0))
    bmp.write(struct.pack('<I', colorsize))
    bmp.write(struct.pack('I', 0x0))

    # for piece in read_in_chunks(data, size = datasize + math.pow(2, bitdepth) * 4):
    for piece in read_in_chunks(data, size = datasize + palettesize):
        bmp.write(piece)

    bmp.close()
