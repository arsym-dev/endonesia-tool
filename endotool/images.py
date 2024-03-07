import sys
import os
import struct
import json
from PIL import Image
from glob import glob
from endotool.utils import read_in_chunks
from endotool.bmp import write_file
from endotool.png import convert_indexed_colors_to_png, convert_bitmap_to_png, convert_png_to_8bit_indexed
from endotool.file_structures.images import *

TEXTURE_END = 0x04a89800
PALETTE_SIZE = 0x400
DATA_8BIT = 0x08
DATA_32BIT = 0x18

UNKNOWN_SIZES = {0x5A9000: {'width': 256, 'height': 256, 'bitdepth': 24}}


def unpack(fname_exo : str, dir_output : str):
    if len(fname_exo) <= 0:
        print('Please enter a valid EXO.BIN file path.', file = sys.stderr)
        return 2
    try:
        exo = open(fname_exo, 'rb')
    except IOError as e:
        print(e, file = sys.stderr)
        return 2

    os.makedirs(dir_output, exist_ok=True)
    if not os.path.isdir(dir_output):
        print('Output is not a folder.')
        return 2

    pos = 10547*2048
    while pos < TEXTURE_END:
        exo.seek(pos)

        sectionsize = struct.unpack('<I', exo.read(4))[0]
        if sectionsize == 0:
            raise Exception("Invalid value")

        offset_to_start_of_data = struct.unpack('<I', exo.read(4))[0]
        exo.seek(pos + offset_to_start_of_data)

        # Some of these values are just not provided
        if pos in UNKNOWN_SIZES:
            width = UNKNOWN_SIZES[pos]['width']
            height = UNKNOWN_SIZES[pos]['height']
            bitdepth = UNKNOWN_SIZES[pos]['bitdepth']
        else:
            bitdepth = 0
            while bitdepth != DATA_8BIT and bitdepth != DATA_32BIT:
                exo.seek(-1, 1)
                bitdepth = struct.unpack('<B', exo.read(1))[0]
                exo.seek(-1, 1)
            exo.seek(-8, 1)
            width = struct.unpack('<I', exo.read(4))[0]
            height = struct.unpack('<I', exo.read(4))[0]

        png_fname = os.path.join(dir_output, f'{pos/2048:05.0f}-{pos + offset_to_start_of_data:08X}-{bitdepth:02d}' + '.png')
        json_fname = os.path.join(dir_output, f'{pos/2048:05.0f}-{pos + offset_to_start_of_data:08X}-{bitdepth:02d}' + '.json')
        print(f"Processing {png_fname}")

        ## IMAGE PIXEL DATA

        exo.seek(pos + offset_to_start_of_data)

        # 8-bit indexed images are in BGRA format
        if bitdepth == 8:
            palette = exo.read(PALETTE_SIZE)
            indices = exo.read(width * height)
            convert_indexed_colors_to_png(width, height, list(palette), list(indices), png_fname)

        elif bitdepth == 24:
            data = []
            for piece in read_in_chunks(exo, size = width * height * 4):
                data.append(struct.unpack('BBBB', piece))

            convert_bitmap_to_png(width, height, data, png_fname)

        else:
            raise Exception(f"Unsupported bitdepth: {bitdepth}")

        print(f"Wrote PNG")

        # Align position to the next nearest block
        if (exo.tell() % 2048) == 0:
            next_pos = exo.tell()
        else:
            next_pos = (int(exo.tell() / 2048)+1)*2048

        if next_pos == 0x01A60800:
            next_pos = 0x01A61000
        if next_pos == 0x0364A000:
            next_pos = 0x0364A800

        ## IMAGE METADATA
        exo.seek(pos)
        info = PackedImageInfo()
        info.from_buffer(exo)
        ser = info.serialize()

        with open(json_fname, 'w') as file:
            # yaml.dump(ser, file, sort_keys=False)
            file.write(json.dumps(ser, indent=4))

        print(f"Wrote JSON")

        ## FINALIZE LOOP
        pos = next_pos

    print(H3_un3_values)

def rebuild(dir_input : str, fname_exo: str):
    try:
        exo = open(fname_exo, 'rb+')
    except IOError as e:
        print(e, file = sys.stderr)
        return 2

    for path in glob(os.path.join(dir_input, '*-*-*.png')):
        block_idx, offset, bitdepth = os.path.basename(path).split('.')[0].split('-')
        offset = int(offset, 16)
        bitdepth = int(bitdepth)

        print(f"Packing {path}")
        if bitdepth == 8:
            data = convert_png_to_8bit_indexed(path)
            exo.seek(offset)
            exo.write(data)
            print("Complete")
        else:
            raise Exception("Not implemented")




    exo.close()