#!/usr/bin/env python3

import sys
import argparse

sys.path.insert(1, 'modules')

class EndonesiaParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)

parser = EndonesiaParser(
        description = 'This tool packs and unpacks graphics and text assets in the PS2 game, Endonesia.'
        , formatter_class = argparse.ArgumentDefaultsHelpFormatter
        )

subparser = parser.add_subparsers(
        dest = 'cmd'
        , help = 'Available commands'
        )
font_unpack_parser = subparser.add_parser('font-unpack'
        , help = 'Unpack font graphics from ELF file.'
        )

font_unpack_parser.add_argument(
        '-i'
        , '--input'
        , required = True
        , action = 'store'
        , metavar = '[ELF file]'
        , help = 'ELF file to unpack. Normally called "pbpx_952.01".'
        )

font_unpack_parser.add_argument(
        '-o'
        , '--output'
        , required = True
        , action = 'store'
        , metavar = '[font file]'
        , help = 'Output file in bmp format.'
        )

font_pack_parser = subparser.add_parser('font-pack'
        , help = 'Pack font graphics back into ELF file.'
        )

font_pack_parser.add_argument(
        '-i'
        , '--input'
        , required = True
        , action = 'store'
        , metavar = '[font file]'
        , help = 'Font graphics to pack in bmp format.'
        )

font_pack_parser.add_argument(
        '-o'
        , '--output'
        , required = True
        , action = 'store'
        , metavar = '[ELF file]'
        , help = 'ELF file to pack. Normally called "pbpx_952.01".'
        )

script_unpack_parser = subparser.add_parser('script-unpack'
        , help = 'Unpack scripts from the game files.'
        )

script_unpack_parser.add_argument(
        '-p'
        , '--elf-file'
        , required = True
        , action = 'store'
        , metavar = '[ELF file]'
        , help = 'ELF file to extract scripts from. Normally called "pbpx_952.01".'
        )

script_unpack_parser.add_argument(
        '-e'
        , '--exo-bin'
        , required = True
        , action = 'store'
        , metavar = '[exo.bin file]'
        , help = 'exo.bin assets file to extract scripts from.'
        )

script_unpack_parser.add_argument(
        '-r'
        , '--overwrite-csv'
        , action = 'store_true'
        , help = 'The default behavior for unpacking to existing CSV files is to only add new entries and leave the existing ones alone. If this flag is enabled and the CSV output file already exists, existing original textsin the CSV file will be overwritten.'
        )

script_unpack_parser.add_argument(
        '-o'
        , '--output'
        , required = True
        , action = 'store'
        , metavar = '[CSV file]'
        , help = 'CSV file to dump scripts into.'
        )

script_pack_parser = subparser.add_parser('script-pack'
        , help = 'Pack scripts back into the game files.'
        )

script_pack_parser.add_argument(
        '-p'
        , '--elf-file'
        , required = True
        , action = 'store'
        , metavar = '[ELF file]'
        , help = 'ELF file to pack scripts into. Normally called "pbpx_952.01".'
        )

script_pack_parser.add_argument(
        '-e'
        , '--exo-bin'
        , required = True
        , action = 'store'
        , metavar = '[exo.bin file]'
        , help = 'exo.bin assets file to pack scripts into.'
        )

script_pack_parser.add_argument(
        '-i'
        , '--input'
        , required = True
        , action = 'store'
        , metavar = '[CSV file]'
        , help = 'CSV file to pack scripts from.'
        )

args = parser.parse_args()

if args.cmd == 'font-unpack':
    from font import unpack
    unpack(args.input, args.output)
elif args.cmd == 'font-pack':
    from font import pack
    pack(args.input, args.output)
elif args.cmd == 'script-unpack':
    from scripts import unpack
    unpack(args.elf_file, args.exo_bin, args.output, args.overwrite_csv)
elif args.cmd == 'script-pack':
    from scripts import pack
    pack(args.input, args.elf_file, args.exo_bin)

if len(sys.argv)==1:
    parser.print_help(sys.stderr)
    sys.exit(1)

