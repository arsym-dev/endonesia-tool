import sys
import os
import io
import struct
import subprocess
from PIL import Image
from endotool.utils import read_in_chunks
from endotool.bmp import write_file

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

    pos = 0 # 0x005A9000
    while exo.tell() < TEXTURE_END:
        try:
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
            exo.seek(pos + offset_to_start_of_data)

            bmpfile = os.path.join(dir_output, f'{pos:08X}' + '.bmp')
            print(f"Processing {bmpfile}")
            # 8-bit indexed images are in BGRA format
            if bitdepth == 8:
                data = io.BytesIO()
                for piece in read_in_chunks(exo, size = PALETTE_SIZE + width * height):
                    index = exo.tell() - pos - offset_to_start_of_data
                    if index < PALETTE_SIZE:
                        # color = struct.unpack('>I', piece)[0]
                        # r = color >> 0x18 & 0xFF
                        # g = color >> 0x10 & 0xFF
                        # b = color >> 0x8 & 0xFF
                        # a = color & 0xFF
                        # color = b << 0x18 | g << 0x10 | r << 0x8 | a
                        # palettepos = data.tell()
                        # # swap palette order
                        # # swapindex = (((index - 4) / 4) + 24) % 32
                        # # if swapindex < 16:
                        # #     swap = 8 * 4 if swapindex < 8 else -8 * 4
                        # #     data.seek(swap, 1)
                        # data.write(struct.pack('>I', color))
                        # data.seek(palettepos + 4)

                        r, g, b, a = struct.unpack('BBBB', piece)
                        if a == 0x80:
                            a = 0xFF
                        else:
                            a = a*2

                        palettepos = data.tell()
                        # swap palette order
                        # swapindex = (((index - 4) / 4) + 24) % 32
                        # if swapindex < 16:
                        #     swap = 8 * 4 if swapindex < 8 else -8 * 4
                        #     data.seek(swap, 1)
                        data.write(struct.pack('BBBB', b, g, r, a))
                        data.seek(palettepos + 4)
                        
                    else:
                        data.write(piece)

                data.seek(0)
                write_file(data, width, height, bitdepth, bmpfile)
                # write_file(data = data, width = width, height = height, bitdepth = bitdepth, output = bmpfile)

                # Flip image vertically
                # im = Image.open(bmpfile)
                # im = im.transpose(Image.FLIP_TOP_BOTTOM)
                # im.save(bmpfile, format="BMP")
                # subprocess.run(['convert', '-flip', bmpfile, bmpfile])

            elif bitdepth == 24:
                write_file(data = exo, width = width, height = height, bitdepth = 32, output = bmpfile)

                
                im = Image.open(bmpfile)
                # BGR -> RGB
                b, g, r, a = im.split() 
                im = Image.merge("RGBA", (r, g, b, a))
                # Flip image vertically
                im = im.transpose(Image.FLIP_TOP_BOTTOM)
                im.save(bmpfile, format="BMP")

                # subprocess.run(['convert', bmpfile, '-separate', '-swap', '0,2', '-combine', '-flip', bmpfile])
            
            else:
                raise Exception(f"Unsupported bitdepth: {bitdepth}")
            
            print(f"Complete")

            # Align position to the next nearest block
            if (exo.tell() % 2048) == 0:
                pos = exo.tell()
            else:
                pos = (int(exo.tell() / 2048)+1)*2048

        except Exception as e:
            pass
