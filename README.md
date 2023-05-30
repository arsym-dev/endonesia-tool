# Endonesia Tool<!-- omit from toc -->

A tool for packing and unpacking PS2 Endonesia resources.

This tool does not provide the ISO for this game. It will not be provided for you, so please don't ask about it.

### Table of Contents<!-- omit from toc -->

- [Requirements](#requirements)
- [Usage](#usage)
- [Suggested workflow](#suggested-workflow)
  - [1. Extract Font](#1-extract-font)
  - [2. Rebuild Font](#2-rebuild-font)
  - [3. Extract Script](#3-extract-script)
  - [4. Edit Script](#4-edit-script)
  - [5. Rebuild Script](#5-rebuild-script)
  - [6. Rebuild ISO](#6-rebuild-iso)
- [Image Formats](#image-formats)
- [Text Formats](#text-formats)

## Requirements

- Python 3
- [Armips](https://github.com/Kingcom/armips)
- [cdvd2iml5.30](https://mega.nz/file/TzhihCjJ#5JCb_DNUklakDtO1t99ZOY0AI_XWXKUiI2BfZhmvjow)
- Mounted/extracted files from the game ISO

## Usage

Open a console terminal in the root directory of this project. Run:

```bash
python tools/endonesia-tool.py
```

## Suggested workflow

In order to prevent accidentally overwriting your progress, it is recommended that you create backups of the ELF and EXO.BIN files. **It is suggested that you rename your files to `SLPM_620.47.bak` and `EXO.BIN.bak`** as these are the file names used in the following commands.

### 1. Extract Font

```bash
python endonesia-tool.py font-extract -e /path/to/SLPM_620.47.bak -f extracted_font.bmp
```

Using an image editing program, edit the extracted BMP file. Each character is in a 24x24 tile.

Once you're done editing the image, you may save it as either a BMP or PNG image. For convenience, a modified version of the font has been provided in `assets/font_en.png` which has already been modified to use variable font width for English characters.

### 2. Rebuild Font

```bash
python endonesia-tool.py font-rebuild -f path/to/input_font.bmp -ei /path/to/SLPM_620.47.bak -ei /path/to/SLPM_620_font.47
```

The above command will create a fixed width font. That means all characters will have a width of exactly 24 pixels. While this works for fixed-width fonts such as most Japanese and Chinese fonts, it does not look good with variable width languages such as most English fonts.

To fix this, provide a JSON file containing the widths of each character. The JSON file has the following format:

```
{
    "[char]": [pixel width],
    "[another char]": [pixel width],
    ...
}
```

For convenience, a JSON file has been provided in `assets/font_widths.json` that matches the provided `assets/font_en.png`. To rebuild the font, run:

```bash
python endonesia-tool.py font-rebuild -f assets/font_en.png -v assets/font_widths.json -ei /path/to/SLPM_620.47.bak -eo /path/to/SLPM_620_font.47
```

`armips` is needed to make the game use the font width table. Because of the way `armips` works, it assumes the ELF file you're trying to change is called `SLPM_620_font.47`. If your ISO contains an ELF file with a different name, you will have to change this in the first line in `tools/vfw.asm`.

### 3. Extract Script

```bash
python endonesia-tool.py script-extract -e /path/to/SLPM_620.47.bak -x /path/to/ELF.BIN.bak -c script_extracted.csv
```

If you want to overwrite the existing Csv file, use the `-r` flag.

It is suggested to rename the CSV file when editing it to prevent accidentally overwriting it if this command is run again.

### 4. Edit Script

Open the CSV file in a text editor. The CSV has the following format:

| File | ELF Pointer | EXO Block | Text addr | Item num | JP text          | EN text |
| ---- | ----------- | --------- | --------- | -------- | ---------------- | ------- |
| ELF  | 003094c0    | 0         | 00348318  | 2        | 例の少年について |         |

- Your final translated text must appear after the final pipe character (`|`).
- If a line does not contain any text after the final pipe, the original Japanese will be used.
- Editing the JP text column does nothing. Only text in the EN text column will affect the game
- If a row is missing from the CSV, the original Japanese will be used and the file will still rebuild nicely. You can use this to get rid of debug text from your edited CSV file without affecting the game.
- `\\n` signifies a new line
- Hexcode between curly brackets `{}` is used for special characters. Notably `{256E}` is the code that represents the player's name.

### 5. Rebuild Script

It is suggested to rebuild the font first in a separate file (`SLPM_620_font.47`) and use that file as the input for this process.

```bash
python endonesia-tool.py script-rebuild -c script_edited.csv -ei /path/to/SLPM_620_font.47 -eo /path/to/SLPM_620.47 -xi /path/to/EXO.BIN.bak -xo /path/to/EXO.BIN
```

### 6. Rebuild ISO

You will need cdvd2iml5.30 to create the ISO. You can download it from here:

[PlayStation_2_Mastering_tools_Collection-v1.7z](https://mega.nz/file/TzhihCjJ#5JCb_DNUklakDtO1t99ZOY0AI_XWXKUiI2BfZhmvjow)

Run `cdvd2iml5.30.msi` and install it. Once it's installed, run it from the start menu.

<p align="center">
<img src="assets/rebuilding_iso.png">
</p>

1. Use the program to open the file `assets/endonesia.iml`
2. At the bottom, press "Full Path" and navigate the folder that has the folder with the extracted Endonesia files
3. Press the "iml2iso" button

Once you've done this, you should have a "endonesia.iso" file that you can use

## Image Formats

Since the binary data in this game most closely resembles BMP, we will be using indexed 4-bit and 8-bit BMP images for sprites. It is recommended to stay in indexed mode, and not to change the palettes or their order, but this tool attempts to closely match the data and formats used in the game upon packing.

## Text Formats

Text is saved with the EUC-JP encoding.
