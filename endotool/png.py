from PIL import Image

def swap_palette(palette):
    swap_num = 8*4
    for idx in range(0, 256*4, 32*4):
        block1_idx = idx+swap_num
        block2_idx = idx+2*swap_num

        temp = palette[block1_idx:block1_idx+swap_num]
        palette[block1_idx:block1_idx+swap_num] = palette[block2_idx:block2_idx+swap_num]
        palette[block2_idx:block2_idx+swap_num] = temp


def convert_indexed_colors_to_png(width, height, palette, indices, fname):
    # Create a new image with the mode 'P' (8-bit indexed color)
    img = Image.new('P', (width, height))

    swap_palette(palette)

    ## Covert half-byte alpha to full byte
    for i in range(3, len(palette), 4):
        if palette[i] == 0x80:
            palette[i] = 0xFF
        else:
            palette[i] *= 2

    img.putpalette(palette, rawmode='RGBA')
    img.putdata(indices)
    img.save(fname)

    # img2 = Image.new('RGBA', (16, 16))
    # img2.putdata([tuple(palette[x:x+4]) for x in range(0, len(palette), 4) ] )
    # img2.save(fname+"-palette.png")

def convert_bitmap_to_png(width, height, data, fname):
    img = Image.new('RGBA', (width, height))

    ## Covert half-byte alpha to full byte
    for i in range(len(data)):
        if data[i][3] == 0x80:
            data[i] = (data[i][0], data[i][1], data[i][2], 0xFF)
        else:
            data[i] = (data[i][0], data[i][1], data[i][2], data[i][3]*2)

    img.putdata(data)
    img.save(fname)

def convert_png_to_8bit_indexed(fname):
    # Open the RGBA image
    rgba_image = Image.open(fname)

    # Convert the image to indexed mode with an 8-bit palette
    indexed_image = rgba_image.convert("P", palette=Image.ADAPTIVE, colors=256)

    data = indexed_image.getdata()
    palette = indexed_image.getpalette()
    pass