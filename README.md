# Endonesia Tool

A tool for packing and unpacking PS2 Endonesia resources.

This tool does not provide the ISO for this game, and we will not provide it for you, so please don't ask about it.

## Requirements

- Python 3
- Imagemagick
- [Armips](https://github.com/Kingcom/armips)
- Mounted/extracted files from the game ISO

## Usage

Type `python tools/endonesia-tool.py` in the root directory of this project.
You will get more help about all the options and commands available when you type this command.

## Image Formats

Since the binary data in this game most closely resembles BMP, we will be using indexed 4-bit and 8-bit BMP images for sprites. It is recommended to stay in indexed mode, and not to change the palettes or their order, but this tool attempts to closely match the data and formats used in the game upon packing.

## Variable Font Widths

A JSON file containing the widths of each character is needed to include variable font widths in the game. The JSON file has the following format:

```
{
    "[char]": [pixel width],
    "[another char]": [pixel width],
    ...
}
```

`armips` is needed to make the game use the font width table. Because of the way `armips` works, it assumes the ELF file you're trying to change is called `SLPM_620.47`. If your ISO contains an ELF file with a different name, you will have to change this in the first line in `tools/vfw.asm`.

## Roadmap

- Scripts
- exo.bin assets
