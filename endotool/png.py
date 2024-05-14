from PIL import Image, ImagePalette

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

    if rgba_image.mode == "P":
        indexed_image = rgba_image

        # For some reason it doesn't want to read the alpha channel properly so I need to do this
        palette = indexed_image.getpalette('RGBA')
        transparency = rgba_image.info.get("transparency")
        if isinstance(transparency, int):
            ## The value tells us which byte is transparent
            palette[3+4*transparency] = 0

        elif transparency is not None:
            transparency = list(transparency)
            for i in range(len(transparency)):
                palette[3+4*i] = transparency[i]

    else:
        # The RGBA conversion is needed to get the palette transparency correct,
        # otherwise it'll give every color an alpha of 255
        rgba_image = rgba_image.convert("RGBA")

        # Convert the image to indexed mode with an 8-bit palette
        indexed_image = rgba_image.convert("P", palette=Image.ADAPTIVE, colors=256)
        palette = indexed_image.getpalette('RGBA')

    data = indexed_image.getdata()
    swap_palette(palette)

    ## Convert alpha to half-byte
    for i in range(3, len(palette), 4):
        if palette[i] == 0xFF:
            palette[i] = 0x80
        else:
            palette[i] = palette[i] >> 1

    return bytes(palette) + bytes(data)

def convert_png_to_bitmap(fname):
    # Open the RGBA image
    rgba_image = Image.open(fname)

    data = list(rgba_image.tobytes())
    ## Convert alpha to half-byte, and make sure the RGB components are zero for transparent pixels
    for i in range(3, len(data), 4):
        if data[i] == 0xFF:
            data[i] = 0x80
        elif data[i] == 0x00 and data[i-1] == 0xFF and data[i-2] == 0xFF and data[i-3] == 0xFF:
            data[i-1] = 0x00
            data[i-2] = 0x00
            data[i-3] = 0x00
        else:
            data[i] = data[i] >> 1

    return bytes(data)
