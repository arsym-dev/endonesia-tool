#!/usr/bin/env python3

import sys
import argparse
import os
import inspect

from endotool import utils, font, scripts, images

filename = inspect.getframeinfo(inspect.currentframe()).filename
basedir = os.path.dirname(os.path.abspath(filename))
utils.basedir = basedir
# os.path.dirname(os.path.realpath(__file__))

class EndonesiaParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)

parser = EndonesiaParser(
    description = 'This tool rebuilds and extracts graphics and text assets in the PS2 game, Endonesia.',
    formatter_class = argparse.ArgumentDefaultsHelpFormatter
    )

subparser = parser.add_subparsers(
    dest = 'cmd',
    help = 'Available commands'
    )

#########
## Font extract
#########
font_extract_parser = subparser.add_parser('font-extract',
    help = 'Extract font graphics from ELF file.'
    )

font_extract_parser.add_argument(
    '-e',
    # '--elf-file',
    required = True,
    action = 'store',
    metavar = '[input ELF]',
    help = 'ELF file to extract. Normally called "SLPM_620.47".'
    )

font_extract_parser.add_argument(
    '-f',
    # '-font',
    required = True,
    action = 'store',
    metavar = '[output IMAGE]',
    help = 'Output image in BMP format.'
    )

#########
## Font rebuild
#########
font_rebuild_parser = subparser.add_parser('font-rebuild',
    help = 'Rebuild font graphics back into ELF file.'
    )

font_rebuild_parser.add_argument(
    '-f',
    # '-font',
    required = True,
    action = 'store',
    metavar = '[input IMAGE]',
    help = 'Font graphic to rebuild. Can be BMP or PNG.'
    )

font_rebuild_parser.add_argument(
    '-v',
    # '--variable-width',
    required = False,
    action = 'store',
    metavar = '[output JSON]',
    help = 'JSON file used for variable font widths. Requires armips. Variable font width hacks will not be included without this table.'
    )

font_rebuild_parser.add_argument(
    '-ei',
    # '--elf-file',
    required = True,
    action = 'store',
    metavar = '[input ELF]',
    help = 'Input ELF file'
    )

font_rebuild_parser.add_argument(
    '-eo',
    # '--elf-file',
    required = True,
    action = 'store',
    metavar = '[output ELF]',
    help = 'Output ELF file'
    )

#########
## Script extract
#########
script_extract_parser = subparser.add_parser('script-extract',
help = 'Extract scripts from the game files.'
    )

script_extract_parser.add_argument(
    '-e',
    # '--elf-file',
    required = True,
    action = 'store',
    metavar = '[input ELF]',
    help = 'ELF file to extract scripts from. Normally called "SLPM_620.47".'
    )

script_extract_parser.add_argument(
    '-x',
    # '--exofin',
    required = True,
    action = 'store',
    metavar = '[input EXO.BIN]',
    help = 'exo.bin assets file to extract scripts from.'
    )

script_extract_parser.add_argument(
    '-c',
    # '--csv',
    required = True,
    action = 'store',
    metavar = '[output CSV]',
    help = 'CSV file to dump scripts into.'
    )

script_extract_parser.add_argument(
    '-r',
    # '--overwrite-csv',
    action = 'store_true',
    help = 'If this flag is enabled and the CSV output file already exists, the CSV file will be overwritten. Default behavior is to only add new entries and leave the existing ones alone.'
    )

#########
## Script rebuild
#########
script_rebuild_parser = subparser.add_parser('script-rebuild',
    help = 'Rebuild scripts back into the game files.'
    )

script_rebuild_parser.add_argument(
    '-c',
    # '--csv',
    required = True,
    action = 'store',
    metavar = '[input CSV]',
    help = 'CSV file to rebuild scripts from.'
    )

script_rebuild_parser.add_argument(
    '-ei',
    # '--elf-file',
    required = True,
    action = 'store',
    metavar = '[input ELF]',
    help = 'Input ELF file.'
    )

script_rebuild_parser.add_argument(
    '-eo',
    # '--elf-file',
    required = True,
    action = 'store',
    metavar = '[output ELF]',
    help = 'Output ELF file to rebuild scripts into. Normally called "SLPM_620.47".'
    )

script_rebuild_parser.add_argument(
    '-xi',
    # '--exofin',
    required = True,
    action = 'store',
    metavar = '[input EXO.BIN]',
    help = 'Input EXO.BIN assets file.'
    )

script_rebuild_parser.add_argument(
    '-xo',
    # '--exofin',
    required = True,
    action = 'store',
    metavar = '[output EXO.BIN]',
    help = 'Output EXO.BIN assets file to rebuild scripts into.'
    )

#########
## Font extract
#########
image_extract_parser = subparser.add_parser('image-extract',
    help = 'Extract images from ELF file.'
    )

image_extract_parser.add_argument(
    '-x',
    # '--exofin',
    required = True,
    action = 'store',
    metavar = '[input EXO.BIN]',
    help = 'exo.bin assets file to extract scripts from.'
    )

image_extract_parser.add_argument(
    '-o',
    # '--output-folder',
    required = True,
    action = 'store',
    metavar = '[output folder]',
    help = 'directory to dump images into.'
    )

# try:
args = parser.parse_args()

if args.cmd == 'font-extract':
    font.extract(
        fname_elf = args.e,
        fname_font = args.f
        )
elif args.cmd == 'font-rebuild':
    font.rebuild(
        fname_font = args.f,
        variable_width = args.v,
        fname_elf_in = args.ei,
        fname_elf_out = args.eo,
    )
elif args.cmd == 'script-extract':
    scripts.extract(
        fname_elf = args.e,
        fname_exo = args.x,
        fname_csv = args.c,
        overwrite = args.r
        )
elif args.cmd == 'script-rebuild':
    scripts.rebuild(
        fname_csv = args.c,
        fname_elf_in = args.ei,
        fname_elf_out = args.eo,
        fname_exo_in = args.xi,
        fname_exo_out = args.xo,
    )
elif args.cmd == 'image-extract':
    images.unpack(
        fname_exo = args.x,
        dir_output = args.o,
    )
#     scripts.calculateFreeSpace(args.elf_file, args.exo_bin)

if len(sys.argv)==1:
    parser.print_help(sys.stderr)
    sys.exit(1)

# except IOError as e:
    # print(e, file = sys.stderr)
    # sys.exit(2)