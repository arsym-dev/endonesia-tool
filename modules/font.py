import subprocess
import tempfile
import struct
import os
from bmp import write_file
from utils import read_in_chunks

OFFSET = 0xD890
WIDTH = 2256
HEIGHT = 1128
BITDEPTH = 4

def unpack(input, output):
    if len(input) <= 0:
        print('Please enter a valid ELF file path.', file = stderr)
        return 2
    try:
        elf = open(input, 'rb')
    except IOError as e:
        print(e, file = stderr)
        return 2

    elf.seek(OFFSET)

    write_file(elf, WIDTH, HEIGHT, BITDEPTH, output)

    subprocess.run(['convert', '-flip', output, output])

def pack(input, output):
    font = tempfile.NamedTemporaryFile(delete = False)
    font.close()
    try:
        palettepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'palettes', 'font-color.bmp')
        subprocess.check_call(['convert', '-flip', '-colors', '16', '-type', 'palette', '-map', palettepath, input, 'BMP2:' + font.name])
    except subprocess.CalledProcessError:
        print('Input font graphics file not found or not the correct format.')
        return 2

    try:
        font = open(font.name, 'rb')
    except IOError as e:
        print(e, file = stderr)
        return 2

    try:
        elf = open(output, 'rb+')
    except IOError as e:
        print(e, file = stderr)
        return 2
    font.seek(0x02)
    filesize = struct.unpack('<I', font.read(4))[0]

    font.seek(0x0A)
    headersize = struct.unpack('<I', font.read(4))[0]
    font.seek(0x12)
    width = struct.unpack('<H', font.read(2))[0]
    height = struct.unpack('<H', font.read(2))[0]

    if width != WIDTH or height != HEIGHT:
        print('Source file needs to have the dimensions 2256x128.')
        return 2
    datasize = filesize - headersize

    font.seek(headersize - 16 * 3)

    # Palette needs to be in a specific order for alpha transparency to work correctly
    palette = []
    palette_map = {}
    for i in range (0, 16):
        color = struct.unpack('<I', font.read(4))[0]
        font.seek(-1, 1)
        color = color - (int(color / 0x1000000) * 0x1000000)
        if color != 0x79B441:
            color = color + 0x80000000

        palette.append(color)
    ordered = palette.copy()
    ordered.sort()

    for i in range (0, 16):
        palette_map[ordered[i]] = i

    indexed = []

    for i in range (0, 16):
        indexed.append(palette_map[palette[i]])

    elf.seek(OFFSET)

    for i in range (0, 16):
        elf.write(struct.pack('<I', ordered[i]))

    font.seek(headersize)

    for piece in read_in_chunks(font, chunk_size = 1, size = datasize + 16 * 4):
        pixel = struct.unpack('B', piece)[0]
        left = pixel >> 4
        right = pixel % 0x10
        newpixel = (indexed[left] << 4) + indexed[right]
        elf.write(struct.pack('B', newpixel))
