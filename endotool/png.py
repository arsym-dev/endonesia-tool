from PIL import Image

def convert_indexed_colors_to_png(width, height, palette, indices, fname):
    # Create a new image with the mode 'P' (8-bit indexed color)
    img = Image.new('P', width, height)
    img.putpalette(palette)
    img.putdata(indices)
    img.save(fname)