import subprocess
import tempfile
import struct
import os
import sys
import json
from PIL import Image

from endotool import tbl
from endotool.bmp import write_file
from endotool.utils import read_in_chunks, check_bin, basedir

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

    # Flip image vertically
    im = Image.open(output)
    im = im.transpose(Image.FLIP_TOP_BOTTOM)
    im.save(output, format="BMP")

    # subprocess.run(['convert', '-flip', output, output])

def pack(input, output, variable_width = False):
    try:
        elf = open(output, 'rb+')
    except IOError as e:
        print(e, file = sys.stderr)
        return 2
    
    img = Image.open(input)
    # img = img.transpose(Image.FLIP_TOP_BOTTOM)
    ## Reduce to a 4 bit pallete. Adaptive prevents dithering
    img = img.convert('P', palette=Image.ADAPTIVE, colors=16)

    width = img.width
    height = img.height

    if width != WIDTH or height != HEIGHT:
        print(f'Source file needs to have the dimensions {WIDTH}x{HEIGHT}. Got {width}x{height}')
        return 2
    
    #####
    ## Palette needs to be in a specific order for alpha transparency to work correctly
    #####
    ## Get the palette as a liste of (R,B,G) tuples
    palette = img.getpalette()
    palette_tuples = [(palette[i], palette[i + 1], palette[i + 2]) for i in range(0, len(palette), 3)]

    palette = []
    palette_map = {}
    for i in range (0, 16):
        tup = palette_tuples[i]
        color = tup[0]<<16 | tup[1]<<8 | tup[2]
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

    #####
    ## Write the pallete to file
    #####
    elf.seek(OFFSET)

    for i in range (0, 16):
        elf.write(struct.pack('<I', ordered[i]))

    #####
    ## Write pixel data
    #####
    pixels = img.getdata()
    for i in range(0, width*height, 2):
        left = pixels[i]
        right = pixels[i+1]
        newpixel = (indexed[left] << 4) + indexed[right]
        elf.write(struct.pack('B', newpixel))

    if variable_width:
        try:
            widths_file = open(variable_width, 'r', encoding='utf-8')
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
            vfwpath = os.path.join(basedir, 'vfw.asm')
            subprocess.check_call(['armips', vfwpath, '-root', os.path.dirname(output)])
        except subprocess.CalledProcessError:
            print('armips failed to replace variable font width code.')
            return 2
