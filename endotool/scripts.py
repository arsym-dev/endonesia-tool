from typing import List
import struct
import os
import csv
import sys
import shutil
import math

from endotool import jis208
from endotool.utils import pad_to_nearest
from endotool.file_structures.text import *

CSV_DELIMETER = '|'
CSV_ESCAPECHAR = '\\'
CSV_LINETERMINATOR = '\n'

ELF_ENUM = 'ELF'
EXO_ENUM = 'EXO'
RESERVED = 0x33D600
EXO_POINTERS     = 0x02C8268
EXO_POINTERS_END = 0x02F8D50
ELF_OFFSET = -0x0163F000
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

def extract(fname_elf, fname_exo, fname_csv, overwrite = False):
    elf_file = open(fname_elf, 'rb')
    exo_file = open(fname_exo, 'rb')

    if os.path.exists(fname_csv) and not overwrite:
        print("CSV already exists. Use the overwrite flag if you want to overwrite this file")

    csv_file = open(fname_csv, 'w', encoding='utf-8')
    writer = csv.writer(csv_file, delimiter=CSV_DELIMETER, escapechar=CSV_ESCAPECHAR, lineterminator=CSV_LINETERMINATOR)
    writer.writerow(["File", "ELF Pointer", "EXO Block", "Text addr", "Item num", "JP text", "EN text"])

    #######
    ## Extract ELF texts
    #######
    elf_mgr = ElfTextManager()
    elf_mgr.readFromFile(elf_file)

    for entry in elf_mgr.text_entries:
        row = [
            ELF_ENUM, # FILE
            dec2hex(entry.elf_address), # ELF Pointer
            0, # EXO Block
            dec2hex(entry.text_address), # Text addr
            entry.item_num, # Item num
            entry.text, # JP Text
            '',# EN Text
        ]
        writer.writerow(row)

    #######
    ## Extract EXO.bin texts
    #######
    print("Reading EXO data")
    blocks = getExoBlocks(elf_file, exo_file)

    print("Writing CSV")
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
                dec2hex(exoblock.exo_address + entry.text_address), # Text addr
                entry.item_num, # Item num
                entry.text, # JP Text
                '',# EN Text
            ]

            writer.writerow(row)
            wrote = True
        
        if wrote:
            writer.writerow([])
    
    elf_file.close()
    exo_file.close()
    csv_file.close()
    print("Done")

def rebuild(fname_csv, fname_elf_in, fname_elf_out, fname_exo_in, fname_exo_out):
    csvfile = open(fname_csv, 'r', encoding='utf-8')

    # Use the backup ELF as the basis for our new write
    elf_file_out = open(fname_elf_out, 'wb+')
    with open(fname_elf_in, 'rb') as elf_file_in:
        elf_file_out.write(elf_file_in.read())

    # Use the backup EXO as the basis for our new write
    exo_file_out = open(fname_exo_out, 'wb+')
    with open(fname_exo_in, 'rb') as exo_file_in:
        exo_file_out.write(exo_file_in.read())

    ## Read all the csv lines
    csv_raw = csvfile.read().replace('\0', '').split('\n')
    reader = csv.reader(csv_raw, delimiter=CSV_DELIMETER, escapechar=CSV_ESCAPECHAR, lineterminator=CSV_LINETERMINATOR)
    csv_data = [r for r in reader]
    csvfile.close()

    ## Pre-process the CSV data
    print("Processing CSV file")
    elf_rows = {}
    exo_rows = {}
    for row in csv_data:
        if len(row)==0:
            continue

        if row[0] == ELF_ENUM:
            elf_pointer = int(row[1], 16)
            if elf_pointer in elf_rows:
                elf_rows[elf_pointer].append(row)
            else:
                elf_rows[elf_pointer] = [row]
        elif row[0] == EXO_ENUM:
            elf_pointer = int(row[1], 16)
            if elf_pointer in exo_rows:
                exo_rows[elf_pointer].append(row)
            else:
                exo_rows[elf_pointer] = [row]

    #######
    ## ELF Blocks
    ## Process EXO rows and add translated text to them
    #######
    print("Reading old ELF data")
    elf_mgr = ElfTextManager()
    elf_mgr.readFromFile(elf_file_out)

    print("Rebuilding ELF file")
    for elf_address, rows in elf_rows.items():
        for row in rows:
            elf_address = int(row[1], 16)
            exo_block = int(row[2], 16)
            text_address = int(row[3], 16)
            item_num = int(row[4])
            text_jp = row[5].strip()
            text_en = row[6].strip()

            found_entry : TextEntry = None
            for entry in elf_mgr.text_entries:
                if elf_address == entry.elf_address and item_num == entry.item_num:
                    found_entry = entry
                    break
            if found_entry is None:
                raise Exception("ELF Entry not found")
            
            if text_en != '':
                found_entry.text = text_en
                found_entry.transform_ascii = True
            else:
                found_entry.text = text_jp
                found_entry.transform_ascii = False
    
    elf_mgr.writeToFile(elf_file_out)
    

    #######
    ## EXO Blocks
    ## Load up the blocks from the original file and save them as-is, but more compressed
    #######
    print("Reading old EXO data")
    blocks = getExoBlocks(elf_file_out, exo_file_out)

    print("Rebuilding EXO file")
    ## Process EXO rows nd add translated text to them
    for elf_pointer, rows in exo_rows.items():
        for row in rows:
            elf_pointer = int(row[1], 16)
            exo_block = int(row[2], 16)
            text_address = int(row[3], 16)
            item_num = int(row[4])
            text_jp = row[5].strip()
            text_en = row[6].strip()

            found_entry : ExoScriptBlock = None
            for entry in blocks:
                if elf_pointer == entry.elf_address:
                    found_entry = entry
                    break
            if found_entry is None:
                raise Exception("EXO Block not found")
            

            found_entry : TextEntry = None
            for entry in entry.text_entries:
                if entry.item_num == item_num:
                    found_entry = entry
                    break
            if found_entry is None:
                raise Exception("EXO Entry not found")

            if text_en != '':
                found_entry.text = text_en
                found_entry.transform_ascii = True
            else:
                found_entry.text = text_jp
                found_entry.transform_ascii = False
        
    
    ## Create the final hex blocks
    curr_exo_address = blocks[0].exo_address

    for entry in blocks:
        bin_data = entry.toBinary()

        ## Adjust the ELF file
        elf_file_out.seek(entry.elf_address)
        elf_file_out.write(struct.pack("<I", entry.exo_size))
        elf_file_out.write(struct.pack("<I", 0))
        elf_file_out.write(struct.pack("<I", curr_exo_address))
        elf_file_out.write(struct.pack("<I", 0))

        ## Write the EXO block
        exo_file_out.seek(curr_exo_address)
        exo_file_out.write(bin_data)

        curr_exo_address += len(pad_to_nearest(bin_data, k=1024))
    
    elf_file_out.close()
    exo_file_out.close()
    print("Done")


def calculateFreeSpace(elf, exo):
    elf_file = open(elf, 'rb')
    exo_file = open(exo, 'rb')

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

