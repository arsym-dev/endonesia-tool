# Endonesia Tool

A tool for packing and unpacking PS2 Endonesia resources.

This tool does not provide the ISO for this game, and we will not provide it for you, so please don't ask about it.

## Requirements

- Python 3
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

A sample json file has been provided in `assets/font_widths.json`, as well as the original font in `assets/font_original.bmp` and a finalized English font in `assets/font_final.png`.

`armips` is needed to make the game use the font width table. Because of the way `armips` works, it assumes the ELF file you're trying to change is called `SLPM_620.47`. If your ISO contains an ELF file with a different name, you will have to change this in the first line in `tools/vfw.asm`.

## Creating the final ISO file

You will need cdvd2iml5.30 to create the ISO. You can download it from here:

PlayStation_2_Mastering_tools_Collection-v1.7z
https://mega.nz/file/TzhihCjJ#5JCb_DNUklakDtO1t99ZOY0AI_XWXKUiI2BfZhmvjow

1. Run cdvd2iml5.30.msi and install it
2. Once it's installed, run it from the start menu
3. Use the program to open the file `assets/endonesia.iml`
4. At the bottom, press "Full Path" and navigate the folder that has the folder ith the extracted Endonesia files
5. Press the "iml2iso" button

Once you've done this, you should have a "endonesia.iso" file that you can use

## Roadmap

- Scripts
- exo.bin assets
