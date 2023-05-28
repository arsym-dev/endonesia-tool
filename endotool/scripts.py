from typing import List
import struct
import os
import csv
import sys
import shutil
import math

from endotool import jis208
from endotool.utils import pad_to_nearest
from endotool.file_structures import *

CSV_DELIMETER = '|'
CSV_ESCAPECHAR = '\\'
CSV_LINETERMINATOR = '\n'

ELF_ENUM = 'ELF'
EXO_ENUM = 'EXO'
RESERVED = 0x33D600
EXO_POINTERS     = 0x02C8268
EXO_POINTERS_END = 0x02F8D50
ELF_OFFSET = -0x163F000
ELF_POINTERS = [
    {
        'pointer': 0x3094C0,
        'size': 2928
    },
    {
        'pointer': 0x310780,
        'size': 752
    },
    {
        'pointer': 0x313310,
        'size': 1000
    },
    {
        'pointer': 0x3497B8,
        'size': 12
    },
    {
        'pointer': 0x330AD0,
        'size': 760
    }
    ]


def string_size(data):
    size = 0
    pos = data.tell()
    while True:
        char = struct.unpack('>H', data.read(2))[0]
        if char == 0x0:
            data.seek(pos)
            return size
        if char % 0x100 == jis208.LINEBREAK:
            data.seek(-1, 1)
            size += 1
        else:
            size += 2

def is_empty(data, size):
    pos = data.tell()
    currentsize = 0
    while currentsize <= size:
        char = struct.unpack('H', data.read(2))[0]
        if char != 0x0:
            data.seek(pos)
            return False
        currentsize += 2

    data.seek(pos)
    return True

def hex_length(string):
    size = len(string)
    length = 0
    i = 0
    while i < size:
        parse = parse_special_char(string, i)
        if parse:
            i += parse['length']
            length += parse['bit_size']
        else:
            i += 1
            length += 2
    return length

def parse_special_char(string, index):
    if jis208.isSpecialStart(string[index]):
        address = '' 
        i = 0
        while True:
            i += 1
            if jis208.isSpecialEnd(string[index + i]):
                i += 1
                break
            address += string[index + i] 
        return {'address': int(address) if address else 0, 'length': i, 'offset': 0, 'bit_size': 2, 'format': '>H'}
    if string[index] == '\\':
        return {'address': jis208.LINEBREAK, 'length': 2, 'offset': -1, 'bit_size': 1, 'format': 'B'}
    return False

def dec2hex(num):
    return "{:08x}".format(num)

def hex2dec(num):
    return hex(num, 16)

def getExoBlocks(elf_file, exo_file) -> List[ExoScriptBlock]:
    #######
    ## Extract EXO.bin texts
    #######
    elf_file.seek(EXO_POINTERS)
    blocks : List[ExoScriptBlock] = []

    while True:
        elf_address = elf_file.tell()
        if elf_address >= EXO_POINTERS_END:
            break

        # print(f"Processing EXO block at ELF address {dec2hex(elf_address)}")

        exo_size = struct.unpack('<I', elf_file.read(4))[0]
        unknown = struct.unpack('<I', elf_file.read(4))[0]

        if exo_size == 0 or exo_size == 0xFFFFFFFF:
            continue

        ## I have no idea why this can be non-zero, but when it is that means
        ## this is not an entry that points to an EXO block
        if unknown != 0:
            continue

        exo_address = struct.unpack('<I', elf_file.read(4))[0]
        zeros = struct.unpack('<I', elf_file.read(4))[0]

        ## Go to the block in the EXO file, read it, then save it to csv
        exoblock = ExoScriptBlock(
            exo_size=exo_size,
            elf_address=elf_address,
            exo_address=exo_address
        )
        exoblock.fromBinary(exo_file)

        blocks.append(exoblock)
    return blocks

def extract(elf, exo, output, overwrite = False):
    try:
        elf_file = open(elf, 'rb')
    except IOError as e:
        print(e, file = sys.stderr)
        return 2

    try:
        exo_file = open(exo, 'rb')
    except IOError as e:
        print(e, file = sys.stderr)
        return 2

    if os.path.exists(output) and not overwrite:
            print("CSV already exists. Use the overwrite flag if you want to overwrite this file")

    try:
        output_file = open(output, 'w', encoding='utf-8')
        writer = csv.writer(output_file, delimiter=CSV_DELIMETER, escapechar=CSV_ESCAPECHAR, lineterminator=CSV_LINETERMINATOR)
        writer.writerow(["File", "ELF Pointer", "EXO Block", "Text addr", "Item num", "JP text", "EN text"])
    except IOError as e:
        print(e, file = sys.stderr)
        return 2

    elf_file.seek(0, os.SEEK_END)
    elfsize = elf_file.tell()

    #######
    ## Extract ELF texts
    #######
    for i in ELF_POINTERS:
        elf_pointer = i['pointer']
        currentpos = elf_pointer
        currentitem = 0
        while currentitem*4 < i['size']:
            elf_file.seek(currentpos)
            text_pointer = struct.unpack('<I', elf_file.read(4))[0] + ELF_OFFSET
            currentpos = elf_file.tell()
            currentitem += 1

            if text_pointer < 0x0 or text_pointer >= elfsize:
                # not a valid pointer
                continue

            elf_file.seek(text_pointer)
            text = jis208.decode(elf_file)

            ## Write output
            if text:
                row = [
                    ELF_ENUM, # FILE
                    dec2hex(elf_pointer), # ELF Pointer
                    0, # EXO Block
                    dec2hex(text_pointer), # Text addr
                    currentitem-1, # Item num
                    text, # JP Text
                    '',# EN Text
                ]
                writer.writerow(row)

    #######
    ## Extract EXO.bin texts
    #######
    blocks = getExoBlocks(elf_file, exo_file)

    ## Write output
    for exoblock in blocks:
        wrote = False
        for entry in exoblock.text_entries:

            # Only print non-duplicated blocks
            if entry.is_duplicate:
                continue

            row = [
                EXO_ENUM, # FILE
                dec2hex(exoblock.elf_address), # ELF Pointer
                dec2hex(exoblock.exo_address), # EXO Block
                dec2hex(exoblock.exo_address + entry.offset), # Text addr
                entry.item_num, # Item num
                entry.text, # JP Text
                '',# EN Text
            ]

            writer.writerow(row)
            wrote = True
        
        if wrote:
            writer.writerow([])

def rebuild(input, elf, exo):

    try:
        csvfile = open(input, 'r', encoding='utf-8')
    except IOError as e:
        print(e, file = sys.stderr)
        return 2

    # Back up the elf file first
    # Then use the backup as the basis for our new write
    if not os.path.exists(elf+".bak"):
        shutil.copyfile(elf, elf+".bak")
    else:
        shutil.copyfile(elf+".bak", elf)

    try:
        elf_file = open(elf, 'rb+')
    except IOError as e:
        print(e, file = sys.stderr)
        return 2

    # Back up the exo file first
    # Then use the backup as the basis for our new write
    if not os.path.exists(exo+".bak"):
        shutil.copyfile(exo, exo+".bak")
    else:
        shutil.copyfile(exo+".bak", exo)

    try:
        exo_file = open(exo, 'rb+')
    except IOError as e:
        print(e, file = sys.stderr)
        return 2

    ## Read all the csv lines
    csv_raw = csvfile.read().replace('\0', '').split('\n')
    reader = csv.reader(csv_raw, delimiter=CSV_DELIMETER, escapechar=CSV_ESCAPECHAR, lineterminator=CSV_LINETERMINATOR)
    csv_data = [r for r in reader]
    csvfile.close()

    ## Pre-process the CSV data
    elf_rows = []
    exo_rows = {}
    for row in csv_data:
        if len(row)==0:
            continue

        if row[0] == ELF_ENUM:
            elf_rows.append(row)
        elif row[0] == EXO_ENUM:
            elf_pointer = int(row[1], 16)
            if elf_pointer in exo_rows:
                exo_rows[elf_pointer].append(row)
            else:
                exo_rows[elf_pointer] = [row]

    # ## Process ELF rows
    # for row in csv_data:
    #     text = row[3] if not row[4] or row[4] == ' ' else row[4]
    #     required_size = hex_length(text)
        
    #     elf_file.seek(int(row[1], 16))
    #     available_size = string_size(elf_file)
    #     if required_size > available_size:
    #         elf_file.seek(reserved_pointer)
    #         if not is_empty(elf_file, required_size):
    #             print('Not enough reserved space left in the ELF file.')
    #             return 2
    #         elf_file.seek(int(row[0], 16))
    #         elf_file.write(struct.pack('<I', reserved_pointer))
    #         elf_file.seek(reserved_pointer)
    #         reserved_pointer += required_size + 2

    #     size = len(text)
    #     i = 0
    #     while i < size:
    #         char = text[i]
    #         parse = parse_special_char(text, i)
    #         pack_format = '>H'
    #         if parse:
    #             hex_value = int(parse['address'])
    #             i += parse['length']
    #             pack_format = parse['format']
    #         else:
    #             hex_value = jis208.convertToHex(char)
    #             i += 1
    #         elf_file.write(struct.pack(pack_format, hex_value))
    

    #######
    ## Load up the blocks from the original file and save them as-is, but more compressed
    #######
    blocks = getExoBlocks(elf_file, exo_file)

    ## Process EXO rows nd add translated text to them
    for elf_pointer, rows in exo_rows.items():
        for row in rows:
            elf_pointer = int(row[1], 16)
            exo_block = int(row[2], 16)
            text_address = int(row[3], 16)
            item_num = int(row[4])
            text_jp = row[5].strip()
            text_en = row[6].strip()

            found_block : ExoScriptBlock = None
            for block in blocks:
                if elf_pointer == block.elf_address:
                    found_block = block
                    break
            if found_block is None:
                raise Exception("Block not found")
            

            found_entry : ExoScriptTextEntry = None
            for entry in block.text_entries:
                if entry.item_num == item_num:
                    found_entry = entry
                    break
            if found_entry is None:
                raise Exception("Entry not found")

            if text_en != '':
                found_entry.text = text_en
                found_entry.transform_ascii = True
            else:
                found_entry.text = text_jp
                found_entry.transform_ascii = False
        
    
    ## Create the final hex blocks
    curr_exo_address = blocks[0].exo_address

    for block in blocks:
        bin_data = block.toBinary()

        ## Adjust the ELF file
        elf_file.seek(block.elf_address)
        elf_file.write(struct.pack("<I", block.exo_size))
        elf_file.write(struct.pack("<I", 0))
        elf_file.write(struct.pack("<I", curr_exo_address))
        elf_file.write(struct.pack("<I", 0))

        ## Write the EXO block
        exo_file.seek(curr_exo_address)
        exo_file.write(bin_data)

        curr_exo_address += len(pad_to_nearest(bin_data, k=1024))
    
    elf_file.close()
    exo_file.close()


def calculateFreeSpace(elf, exo):
    try:
        elf_file = open(elf, 'rb')
    except IOError as e:
        print(e, file = sys.stderr)
        return 2

    try:
        exo_file = open(exo, 'rb')
    except IOError as e:
        print(e, file = sys.stderr)
        return 2

    #######
    ## Extract EXO.bin texts
    #######
    elf_file.seek(EXO_POINTERS)

    prev_block_val = 0

    text_bytes = 0
    free_bytes = 0

    blocks = getExoBlocks(elf_file, exo_file)
    for exoblock in blocks:

        block_val = exoblock.exo_address/2048
        if block_val != prev_block_val:
            print("Non consequtive block detected")

        remaining_size_in_block = 2048 - exoblock.exo_size%2048

        print(f"""
ELF: {exoblock.elf_address:08X} |
Exo: {exoblock.exo_address:08X} |
Blocks: {exoblock.exo_address/2048:0.0f} + {math.ceil(exoblock.exo_size/2048):3.0f} |
Text bytes: {exoblock.text_size:5d} |
Free bytes: {remaining_size_in_block:4d}
""".replace("\n", " "), end="")

        if (exoblock.text_size > 0):
            print(f"| Percentage Free: {100*(remaining_size_in_block/exoblock.text_size):0.1f}%")
        else:
            print("")
        
        text_bytes += exoblock.text_size
        free_bytes += remaining_size_in_block

        prev_block_val = block_val + math.ceil(exoblock.exo_size/2048)
    
    print(f"Text: {text_bytes} | Free: {free_bytes}")

