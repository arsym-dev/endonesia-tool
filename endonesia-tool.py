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
        , metavar = 'Input ELF File'
        , help = 'ELF file to unpack. Normally called "pbpx_952.01".'
        )

font_unpack_parser.add_argument(
        '-o'
        , '--output'
        , required = True
        , action = 'store'
        , metavar = 'Output Font File'
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
        , metavar = 'Input Font File'
        , help = 'Font graphics to pack in bmp format.'
        )

font_pack_parser.add_argument(
        '-o'
        , '--output'
        , required = True
        , action = 'store'
        , metavar = 'Output ELF File'
        , help = 'ELF file to pack. Normally called "pbpx_952.01".'
        )

args = parser.parse_args()

print(vars(args))

if args.cmd == 'font-unpack':
    from font import unpack
    unpack(args.input, args.output)
elif args.cmd == 'font-pack':
    from font import pack
    pack(args.input, args.output)

if len(sys.argv)==1:
    parser.print_help(sys.stderr)
    sys.exit(1)

