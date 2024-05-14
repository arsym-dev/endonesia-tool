import subprocess
import struct
import os
import json
import shutil
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

def extract(fname_elf, fname_font):
    print("Extracting font image")
    elf_file = open(fname_elf, 'rb')
    elf_file.seek(OFFSET)

    write_file(elf_file, WIDTH, HEIGHT, BITDEPTH, fname_font)

    # Flip image vertically
    im = Image.open(fname_font)
    im = im.transpose(Image.FLIP_TOP_BOTTOM)
    im.save(fname_font, format="BMP")

    print("Done")


def rebuild(fname_font, fname_elf_in, fname_elf_out, variable_width = False):
    elf_file_out = open(fname_elf_out, 'wb')

    ## Copy the input
    with open(fname_elf_in, 'rb') as elf_file_in:
        elf_file_out.write(elf_file_in.read())


    ########
    ## Format font image
    ########
    print("Processing font image")
    img = Image.open(fname_font)
    # img = img.transpose(Image.FLIP_TOP_BOTTOM)
    ## Reduce to a 4 bit pallete. Adaptive prevents dithering
    img = img.convert('P', palette=Image.ADAPTIVE, colors=16)

    width = img.width
    height = img.height

    if width != WIDTH or height != HEIGHT:
        print(f'Source file needs to have the dimensions {WIDTH}x{HEIGHT}. Got {width}x{height}')
        return 2

    ## Palette needs to be in a specific order for alpha transparency to work correctly
    ## Get the palette as a list of (R,B,G) tuples
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
    print("Writing font image")
    elf_file_out.seek(OFFSET)

    for i in range (0, 16):
        elf_file_out.write(struct.pack('<I', ordered[i]))

    #####
    ## Write pixel data
    #####
    pixels = img.getdata()
    for i in range(0, width*height, 2):
        left = pixels[i]
        right = pixels[i+1]
        newpixel = (indexed[left] << 4) + indexed[right]
        elf_file_out.write(struct.pack('B', newpixel))

    if variable_width:
        print("Processing variable font widths")
        widths_file = open(variable_width, 'r', encoding='utf-8')
        widths_table = json.load(widths_file)
        widths_data = [0x18] * TABLE_SIZE

        table = tbl.TBL(tbl.TBL.PACK)

        for char in widths_table:
            index = table.pos(char)
            if index >= 0:
                widths_data[index] = widths_table[char]

        elf_file_out.seek(WIDTH_TABLE)

        for i in range(0, TABLE_SIZE):
            elf_file_out.write(struct.pack('B', widths_data[i]))

        elf_file_out.close()

        if not check_bin('armips'):
            print('Font successfully packed, but variable font widths are not installed because armips is not in your path.')
            return 2

        try:
            out_dir = os.path.dirname(fname_elf_out)
            shutil.copy('vfw.asm', out_dir)
            # vfwpath = os.path.join(basedir, 'vfw.asm')
            subprocess.check_call(['armips', 'vfw.asm', '-root', out_dir])
        except subprocess.CalledProcessError:
            print('armips failed to replace variable font width code.')
            return 2

    print("Done")
