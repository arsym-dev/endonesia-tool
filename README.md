# Endonesia Tool 

A tool for packing and unpacking PS2 Endonesia resources.

This tool does not provide the ISO for this game, and we will not provide it for you, so please don't ask about it.

## Requirements

* Python 3
* Imagemagick
* Mounted/extracted files from the game ISO

## Usage

Type `python endonesia-tool.py` in the root directory of this project.
You will get more help about all the options and commands available when you type this command.

## Image Formats

Since the binary data in this game most closely resembles BMP, we will be using indexed 4-bit and 8-bit BMP images for sprites. It is recommended to stay in indexed mode, and not to change the palettes or their order, but this tool attempts to closely match the data and formats used in the game upon packing.

## Roadmap

* Scripts
* exo.bin assets
