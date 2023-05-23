import subprocess
import tempfile
import struct
import os
import sys
import json

from endotool import tbl
from endotool.bmp import write_file
from endotool.utils import read_in_chunks, check_bin, tooldir

OFFSET = 0xD890
WIDTH = 2256
HEIGHT = 1128
BITDEPTH = 4
WIDTH_TABLE = 0x33D4D0
TABLE_SIZE = 0x11A

def unpack(input, output):
    if len(input) <= 0:
        print('Please enter a valid ELF file path.', file = sys.stderr)
        return 2
    try:
        elf = open(input, 'rb')
    except IOError as e:
        print(e, file = sys.stderr)
        return 2

    elf.seek(OFFSET)

    write_file(elf, WIDTH, HEIGHT, BITDEPTH, output)

    subprocess.run(['convert', '-flip', output, output])

def pack(input, output, variable_width = False):
    # font = tempfile.NamedTemporaryFile(delete = False)
    # font.close()
    # try:
    #     palettepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'palettes', 'font-color.bmp')
    #     subprocess.check_call(['convert', '-flip', '-colors', '16', '-type', 'palette', '-map', palettepath, input, 'BMP2:' + font.name])
    # except subprocess.CalledProcessError:
    #     print('Input font graphics file not found or not the correct format.')
    #     return 2

    # try:
    #     font = open(font.name, 'rb')
    # except IOError as e:
    #     print(e, file = sys.stderr)
    #     return 2

    try:
        elf = open(output, 'rb+')
    except IOError as e:
        print(e, file = sys.stderr)
        return 2
    # font.seek(0x02)
    # filesize = struct.unpack('<I', font.read(4))[0]

    # font.seek(0x0A)
    # headersize = struct.unpack('<I', font.read(4))[0]
    # font.seek(0x12)
    # width = struct.unpack('<H', font.read(2))[0]
    # height = struct.unpack('<H', font.read(2))[0]

    # if width != WIDTH or height != HEIGHT:
    #     print('Source file needs to have the dimensions 2256x128.')
    #     return 2
    # datasize = filesize - headersize

    # font.seek(headersize - 16 * 3)

    # # Palette needs to be in a specific order for alpha transparency to work correctly
    # palette = []
    # palette_map = {}
    # for i in range (0, 16):
    #     color = struct.unpack('<I', font.read(4))[0]
    #     font.seek(-1, 1)
    #     color = color - (int(color / 0x1000000) * 0x1000000)
    #     if color != 0x79B441:
    #         color = color + 0x80000000

    #     palette.append(color)
    # ordered = palette.copy()
    # ordered.sort()

    # for i in range (0, 16):
    #     palette_map[ordered[i]] = i

    # indexed = []

    # for i in range (0, 16):
    #     indexed.append(palette_map[palette[i]])

    # elf.seek(OFFSET)

    # for i in range (0, 16):
    #     elf.write(struct.pack('<I', ordered[i]))

    # font.seek(headersize)

    # for piece in read_in_chunks(font, chunk_size = 1, size = datasize + 16 * 4):
    #     pixel = struct.unpack('B', piece)[0]
    #     left = pixel >> 4
    #     right = pixel % 0x10
    #     newpixel = (indexed[left] << 4) + indexed[right]
    #     elf.write(struct.pack('B', newpixel))

    if variable_width:
        try:
            widths_file = open(variable_width, 'r')
        except IOError as e:
            print(e, file = sys.stderr)
            return 2

        table = tbl.TBL(tbl.TBL.PACK)

        widths_table = json.load(widths_file)

        widths_data = [0x18] * TABLE_SIZE

        for char in widths_table:
            index = table.pos(char)
            if index >= 0:
                widths_data[index] = widths_table[char]

        elf.seek(WIDTH_TABLE)

        for i in range(0, TABLE_SIZE):
            elf.write(struct.pack('B', widths_data[i]))

        if not check_bin('armips'):
            print('Font successfully packed, but variable font widths are not installed because armips is not in your path.')
            return 2

        try:
            vfwpath = os.path.join(tooldir, 'vfw.asm')
            subprocess.check_call(['armips', vfwpath, '-root', output])
        except subprocess.CalledProcessError:
            print('armips failed to replace variable font width code.')
            return 2
