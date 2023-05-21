from typing import List
import struct
import os
import io
import csv
import sys
import shutil
import jis208
import math
from utils import read_in_chunks, csv_find, pad_to_nearest

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


def decode(data):
    text = ''
    while True:
        char = struct.unpack('>H', data.read(2))[0]
        result = jis208.convertToString(char)
        if result == '\\n':
            data.seek(-1, 1)
        if result is False:
            break
        text += result
    return text

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

def unpack(elf, exo, output, overwrite = False):
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
            text = decode(elf_file)

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
    elf_file.seek(EXO_POINTERS)

    while True:
        elf_pointer = elf_file.tell()
        # exo_pointer = struct.unpack('<I', elf_file.read(4))[0]
        # elf_file.seek(0x4, 1)

        exo_size = struct.unpack('<I', elf_file.read(4))[0]
        unknown = struct.unpack('<I', elf_file.read(4))[0]
        exo_pointer = struct.unpack('<I', elf_file.read(4))[0]
        zeros = struct.unpack('<I', elf_file.read(4))[0]

        if elf_pointer >= EXO_POINTERS_END:
            break
        if exo_pointer > 0x06000000 or exo_pointer < 0x04000000:
            continue
        

        ## Go to the block in the EXO file, read it, then save it to csv
        exo_file.seek(exo_pointer)

        exoblock = ExoScriptBlock()
        exoblock.elf_address = elf_pointer
        exoblock.unpack(exo_file)

        ## Write output
        for i, s in enumerate(exoblock.strings):
            row = [
                EXO_ENUM, # FILE
                dec2hex(exoblock.elf_address), # ELF Pointer
                dec2hex(exoblock.exo_address), # EXO Block
                dec2hex(exoblock.exo_address + exoblock.offsets[i]), # Text addr
                i, # Item num
                s, # JP Text
                '',# EN Text
            ]

            writer.writerow(row)
        

def pack(input, elf, exo):
    try:
        csvfile = open(input, 'r', encoding='utf-8')
    except IOError as e:
        print(e, file = sys.stderr)
        return 2

    try:
        elf_file = open(elf, 'rb+')
    except IOError as e:
        print(e, file = sys.stderr)
        return 2

    try:
        exo_file = open(exo, 'rb+')
    except IOError as e:
        print(e, file = sys.stderr)
        return 2

    csv_data = csvfile.read().replace('\0', '').split('\n')
    reader = csv.reader(csv_data, delimiter=CSV_DELIMETER, escapechar=CSV_ESCAPECHAR, lineterminator=CSV_LINETERMINATOR)
    csv_data = [r for r in reader]


    #Prepare for packing
    exodata = []
    exo_pointers = []
    elf_file.seek(EXO_POINTERS)

    exo_file.seek(0, os.SEEK_END)
    original_exo_size = exo_file.tell()
    while True:
        pointer = struct.unpack('<I', elf_file.read(4))[0]
        if pointer == 0x0:
            break
        exo_pointers.append(pointer)
        elf_file.seek(0xC, 1)
    exo_file.seek(exo_pointers[0])
    exo_buffer = io.BytesIO()

    reserved_pointer = RESERVED
    elf_file.seek(RESERVED)
    while True:
        check = struct.unpack('<H', elf_file.read(2))[0]
        if check == 0x0:
            elf_file.seek(2, 1)
            reserved_pointer = elf_file.tell()
            break

    exo_offset = exo_pointers[0]

    for piece in read_in_chunks(exo_file, size = original_exo_size - exo_offset):
        exo_buffer.write(piece)

    for row in csv_data:
        text = row[3] if not row[4] or row[4] == ' ' else row[4]
        required_size = hex_length(text)
        if row[2] == ELF_ENUM:
            elf_file.seek(int(row[1], 16))
            available_size = string_size(elf_file)
            if required_size > available_size:
                elf_file.seek(reserved_pointer)
                if not is_empty(elf_file, required_size):
                    print('Not enough reserved space left in the ELF file.')
                    return 2
                elf_file.seek(int(row[0], 16))
                elf_file.write(struct.pack('<I', reserved_pointer))
                elf_file.seek(reserved_pointer)
                reserved_pointer += required_size + 2

            size = len(text)
            i = 0
            while i < size:
                char = text[i]
                parse = parse_special_char(text, i)
                pack_format = '>H'
                if parse:
                    hex_value = int(parse['address'])
                    i += parse['length']
                    pack_format = parse['format']
                else:
                    hex_value = jis208.convertToHex(char)
                    i += 1
                elf_file.write(struct.pack(pack_format, hex_value))
        elif row[2] == EXO_ENUM:
            elf_file.seek(int(row[0], 16))
            pointer = struct.unpack('<I', elf_file.read(4))[0]
            pointer_index = exo_pointers.index(pointer)

            exo_buffer.seek(pointer - exo_offset)
            exo_newbuffer = io.BytesIO()
            block_size = exo_pointers[pointer_index + 1] - exo_pointers[pointer_index] if pointer_index < len(exo_pointers) else original_exo_size - exo_pointers[pointer_index]
            for piece in read_in_chunks(exo_buffer, size = block_size):
                exo_newbuffer.write(piece)

            exo_newbuffer.seek(0)
            length = struct.unpack('<I', exo_newbuffer.read(4))[0]
            content_length = struct.unpack('<I', exo_newbuffer.read(4))[0]
            exo_newbuffer.seek(int(row[1], 16))
            textpos = struct.unpack('<I', exo_newbuffer.read(4))[0]
            exo_newbuffer.seek(textpos)
            print(f"{hex(textpos)}\t{length}\t{content_length}\t0x{row[1]}\t0x{row[0]}, {int(row[1], 16)}, {int(row[0], 16)}")
            available_size = string_size(exo_newbuffer)
            if available_size < required_size:
                sizediff = required_size - available_size + (-required_size % 0x8)
                exo_newbuffer.seek(content_length)
                text_pointers = []
                for piece in read_in_chunks(exo_newbuffer, size = length - content_length):
                    text_pointers.append(struct.unpack('<I', piece)[0])

                size = len(text_pointers)
                for i in range(0, size):
                    if text_pointers[i] > textpos:
                        text_pointers[i] += sizediff

                exo_newbuffer.seek(content_length)
                for i in range(0, size):
                    exo_newbuffer.write(struct.pack('<I', text_pointers[i]))

                exo_backbuffer = io.BytesIO()
                exo_newbuffer.seek(textpos + available_size)

                #Shift everything in the block down
                backbuffer_size = length - exo_newbuffer.tell()
                for piece in read_in_chunks(exo_newbuffer, size = backbuffer_size):
                    exo_backbuffer.write(piece)

                exo_newbuffer.seek(textpos)

            size = len(text)
            i = 0
            while i < size:
                char = text[i]
                parse = parse_special_char(text, i)
                pack_format = '>H'
                if parse:
                    hex_value = int(parse['address'])
                    i += parse['length']
                    pack_format = parse['format']
                else:
                    hex_value = jis208.convertToHex(char)
                    i += 1
                exo_newbuffer.write(struct.pack(pack_format, hex_value))

            if available_size < required_size:
                padsize = required_size % 0x8
                for i in range(0, padsize):
                    exo_newbuffer.write(struct.pack('B', 0))

                exo_newbuffer.seek(-sizediff, os.SEEK_END)
                for piece in read_in_chunks(exo_backbuffer):
                    exo_newbuffer.write(piece)
                exo_backbuffer.close()

                exo_newbuffer.seek(0)
                exo_newbuffer.write(struct.pack('<I', length + sizediff))
                exo_newbuffer.write(struct.pack('<I', content_length + sizediff))

                #Check if we need to shift all the other blocks below the current one
                if not is_empty(exo_newbuffer, sizediff):
                    blockdiff = sizediff + (-sizediff % 0x800)
                    exo_backbuffer = io.BytesIO()
                    exo_buffer.seek(pointer - exo_offset + length)
                    for piece in read_in_chunks(exo_buffer):
                        exo_backbuffer.write(piece)

                    exo_newbuffer.seek(0)
                    exo_buffer.seek(pointer - exo_offset)
                    for piece in read_in_chunks(exo_newbuffer):
                        exo_buffer.write(piece)

                    for i in range(0, -sizediff % 0x800):
                        exo_buffer.write(struct.pack('B', 0))

                    for piece in read_in_chunks(exo_backbuffer):
                        exo_buffer.write(piece)

                    exo_backbuffer.close()

                    size = len(exo_pointers)
                    for i in range(pointer_index + 1, size):
                        exo_pointers[i] += blockdiff

            exo_newbuffer.close()

    elf_file.seek(EXO_POINTERS)
    size = len(exo_pointers)
    for i in range(0, size):
        elf_file.write(struct.pack('<I', exo_pointers[i]))
        elf_file.seek(0xC, 1)

    exo_file.seek(exo_offset)
    exo_buffer.seek(0)

    for piece in read_in_chunks(exo_buffer):
        exo_file.write(piece)


def pack2(input, elf, exo):
    # b = ExoScriptBlock(["I hope you don't mind monospaced fonts"])
    # rv = b.pack()

    # for i, b in enumerate(rv):
    #     if i % 16 == 0:
    #         print("\n", end="")
    #     if i % 4 == 0:
    #         print("  ", end="")
        
    #     print(f"{b:02x} ", end="")
    # pass

    try:
        csvfile = open(input, 'r', encoding='utf-8')
    except IOError as e:
        print(e, file = sys.stderr)
        return 2

    ## Back up the elf file first
    ## Then use the backup as the basis for our new write
    # if not os.path.exists(elf+".bak"):
    #     shutil.copyfile(elf, elf+".bak")
    # else:
    #     shutil.copyfile(elf+".bak", elf)

    try:
        elf_file = open(elf, 'rb+')
    except IOError as e:
        print(e, file = sys.stderr)
        return 2

    ## Back up the exo file first
    ## Then use the backup as the basis for our new write
    # if not os.path.exists(exo+".bak"):
    #     shutil.copyfile(exo, exo+".bak")
    # else:
    #     shutil.copyfile(exo+".bak", exo)

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


    # #Prepare for packing
    # exodata = []
    # exo_pointers = []
    # elf_file.seek(EXO_POINTERS)

    # exo_file.seek(0, os.SEEK_END)
    # original_exo_size = exo_file.tell()
    # while True:
    #     pointer = struct.unpack('<I', elf_file.read(4))[0]
    #     if pointer == 0x0:
    #         break
    #     exo_pointers.append(pointer)
    #     elf_file.seek(0xC, 1)
    # exo_file.seek(exo_pointers[0])
    # exo_buffer = io.BytesIO()

    # reserved_pointer = RESERVED
    # elf_file.seek(RESERVED)
    # while True:
    #     check = struct.unpack('<H', elf_file.read(2))[0]
    #     if check == 0x0:
    #         elf_file.seek(2, 1)
    #         reserved_pointer = elf_file.tell()
    #         break

    # exo_offset = exo_pointers[0]

    # for piece in read_in_chunks(exo_file, size = original_exo_size - exo_offset):
    #     exo_buffer.write(piece)

    elf_rows = []
    exo_rows = {}
    for row in csv_data:
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
    

    ## Process EXO rows
    for elf_pointer, rows in exo_rows.items():
        strings = []
        for row in rows:
            elf_pointer = row[1]
            exo_block = row[2]
            text_address = row[3]
            item_num = row[4]
            text_jp = row[5].strip()
            text_en = row[6].strip()

            entry = ExoScriptString()
            entry.item_num = item_num
            entry.offset = text_address

            if text_en != '':
                entry.string = text_en
            else:
                entry.string = text_jp
            
            strings.append(entry)
        
        ## Create the final hex block
        exoblock = ExoScriptBlock(strings)
        exoblock.transform_ascii = True
        rv = exoblock.pack()
        rv = pad_to_nearest(rv, k=2048)

        # b = ExoScriptBlock(["I hope you don't mind monospaced fonts"])
        # rv = b.pack()

        for i, b in enumerate(rv):
            if i % 16 == 0:
                print("\n", end="")
            if i % 4 == 0:
                print("  ", end="")
            
            print(f"{b:02x} ", end="")
        pass

        # ## Insert at the bottom of the EXO file
        # exo_file.seek(0, os.SEEK_END)
        # exo_pointer = exo_file.tell()
        # exo_file.write(rv)
    
        # ## Rewrite the ELF pointer to point to this new EXO address
        # elf_file.seek(elf_pointer, os.SEEK_SET)
        # elf_file.write(struct.pack("<I", exo_pointer))


    exo_file.close()
    elf_file.close()


        

    #     text = row[3] if not row[4] or row[4] == ' ' else row[4]
    #     required_size = hex_length(text)
        
    #     elf_file.seek(int(row[0], 16))
    #     pointer = struct.unpack('<I', elf_file.read(4))[0]
    #     pointer_index = exo_pointers.index(pointer)

    #     exo_buffer.seek(pointer - exo_offset)
    #     exo_newbuffer = io.BytesIO()
    #     block_size = exo_pointers[pointer_index + 1] - exo_pointers[pointer_index] if pointer_index < len(exo_pointers) else original_exo_size - exo_pointers[pointer_index]
    #     for piece in read_in_chunks(exo_buffer, size = block_size):
    #         exo_newbuffer.write(piece)

    #     exo_newbuffer.seek(0)
    #     length = struct.unpack('<I', exo_newbuffer.read(4))[0]
    #     content_length = struct.unpack('<I', exo_newbuffer.read(4))[0]
    #     exo_newbuffer.seek(int(row[1], 16))
    #     textpos = struct.unpack('<I', exo_newbuffer.read(4))[0]
    #     exo_newbuffer.seek(textpos)
    #     print(f"{hex(textpos)}\t{length}\t{content_length}\t0x{row[1]}\t0x{row[0]}, {int(row[1], 16)}, {int(row[0], 16)}")
    #     available_size = string_size(exo_newbuffer)
    #     if available_size < required_size:
    #         sizediff = required_size - available_size + (-required_size % 0x8)
    #         exo_newbuffer.seek(content_length)
    #         text_pointers = []
    #         for piece in read_in_chunks(exo_newbuffer, size = length - content_length):
    #             text_pointers.append(struct.unpack('<I', piece)[0])

    #         size = len(text_pointers)
    #         for i in range(0, size):
    #             if text_pointers[i] > textpos:
    #                 text_pointers[i] += sizediff

    #         exo_newbuffer.seek(content_length)
    #         for i in range(0, size):
    #             exo_newbuffer.write(struct.pack('<I', text_pointers[i]))

    #         exo_backbuffer = io.BytesIO()
    #         exo_newbuffer.seek(textpos + available_size)

    #         #Shift everything in the block down
    #         backbuffer_size = length - exo_newbuffer.tell()
    #         for piece in read_in_chunks(exo_newbuffer, size = backbuffer_size):
    #             exo_backbuffer.write(piece)

    #         exo_newbuffer.seek(textpos)

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
    #         exo_newbuffer.write(struct.pack(pack_format, hex_value))

    #     if available_size < required_size:
    #         padsize = required_size % 0x8
    #         for i in range(0, padsize):
    #             exo_newbuffer.write(struct.pack('B', 0))

    #         exo_newbuffer.seek(-sizediff, os.SEEK_END)
    #         for piece in read_in_chunks(exo_backbuffer):
    #             exo_newbuffer.write(piece)
    #         exo_backbuffer.close()

    #         exo_newbuffer.seek(0)
    #         exo_newbuffer.write(struct.pack('<I', length + sizediff))
    #         exo_newbuffer.write(struct.pack('<I', content_length + sizediff))

    #         #Check if we need to shift all the other blocks below the current one
    #         if not is_empty(exo_newbuffer, sizediff):
    #             blockdiff = sizediff + (-sizediff % 0x800)
    #             exo_backbuffer = io.BytesIO()
    #             exo_buffer.seek(pointer - exo_offset + length)
    #             for piece in read_in_chunks(exo_buffer):
    #                 exo_backbuffer.write(piece)

    #             exo_newbuffer.seek(0)
    #             exo_buffer.seek(pointer - exo_offset)
    #             for piece in read_in_chunks(exo_newbuffer):
    #                 exo_buffer.write(piece)

    #             for i in range(0, -sizediff % 0x800):
    #                 exo_buffer.write(struct.pack('B', 0))

    #             for piece in read_in_chunks(exo_backbuffer):
    #                 exo_buffer.write(piece)

    #             exo_backbuffer.close()

    #             size = len(exo_pointers)
    #             for i in range(pointer_index + 1, size):
    #                 exo_pointers[i] += blockdiff

    #     exo_newbuffer.close()

    # elf_file.seek(EXO_POINTERS)
    # size = len(exo_pointers)
    # for i in range(0, size):
    #     elf_file.write(struct.pack('<I', exo_pointers[i]))
    #     elf_file.seek(0xC, 1)

    # exo_file.seek(exo_offset)
    # exo_buffer.seek(0)

    # for piece in read_in_chunks(exo_buffer):
    #     exo_file.write(piece)

class ExoScriptString:
    item_num : int = 0
    offset : int = 0
    string : str = ""

class ExoScriptBlock:
    """
    ImHex Pattern

    struct ExoScriptBlock {
        // === Structure ===
        // Header: 0x20
        // Text section: variable
        // Text offsets at the bottom
        // A bunch of script data?

        le u32 blockSize;
        le u32 textSize;
        le u32 unknown;
        le u32 zeros[5];
        
        le u32 textOffsets[(blockSize-textSize)/4] @ addressof(blockSize) + textSize;
        char text[textSize-0x20] @ addressof(blockSize) + 0x20;
        
        le u32 fistTextAddress @ addressof(blockSize) + textOffsets[0];
        
        // The end is passed with zeros. The zeroed addresses are NOT read.
        // The lowest a valid textOffset can be is 0x20
    };
    """

    def __init__(self,
                 script_strings : List[ExoScriptString] = None,
                 elf_address : int = 0,
                 exo_address : int = 0) -> None:
        ## ELF data
        ## <exo_size> <zeros> <elf_pointer> <zeros>
        self.exo_size : int = 0 # The size of the EXO block according to the ELF
        self.elf_address : int = elf_address # The address in the ELF file. Contains the value of exo_address
        self.exo_address : int = exo_address # The address of this block in the EXO file

        ## EXO block data
        self.block_size : int = 0
        self.pointer_to_text_offsets : int = 0
        self.unknown : int = 0
        self.script_data : bytearray = b""

        ## EXO data
        self.transform_ascii : bool = False

        if script_strings is None:
            self.script_strings = []
        else:
            self.script_strings = script_strings
        
    
    @property
    def text_size(self):
        return self.pointer_to_text_offsets - 0x20
    
    def unpack(self, exo_file):
        self.script_strings = []
        self.offsets = []
        self.exo_address = exo_file.tell()

        self.block_size = struct.unpack('<I', exo_file.read(4))[0]
        self.pointer_to_text_offsets = struct.unpack('<I', exo_file.read(4))[0]
        self.unknown = struct.unpack('<I', exo_file.read(4))[0]

        if self.elf_address in [0x002C8888]:
            ## I have no idea why this block handles things differently
            self.pointer_to_text_offsets += 0x20

        exo_file.seek(self.exo_address + self.pointer_to_text_offsets)
        currentpos = exo_file.tell()
        currentitem = 0

        while currentitem < (self.block_size - self.pointer_to_text_offsets)/4:
            exo_file.seek(currentpos)
            text_pointer = struct.unpack('<I', exo_file.read(4))[0]
            exo_file.seek(self.exo_address + text_pointer)
            char = struct.unpack('>H', exo_file.read(2))[0]
            
            currentpos += 4
            currentitem += 1
            if jis208.validate(char):
                self.script_strings.append(jis208.convertToString(char) + decode(exo_file))
                self.offsets.append(text_pointer)
            else:
                pass
    
    def pack(self):
        ## Process the strings so they become valid EUC JP
        output_strings = []
        for s in self.script_strings:
            byte_string = jis208.stringToHex(s, transform_ascii=self.transform_ascii)
            output_strings.append(pad_to_nearest(byte_string))
        
        ## Get the length of each of these strings and create an offset,
        ## keeping in mind that the smallest offset is 0x20 to account for the header
        self.offsets = [0x20]
        for i in range(1, len(output_strings)):
            self.offsets.append(self.offsets[-1]+len(output_strings[i-1]))
        
        ## Reverse the string and offset lists and create each section
        # output_strings = output_strings[::-1]
        self.offsets = self.offsets[::-1]

        text_section = b""
        for s in output_strings:
            text_section += s
        
        offset_section = b""
        for off in self.offsets:
            offset_section += struct.pack("<I", off)
        offset_section = pad_to_nearest(offset_section)

        ###########
        ## Finally, write the outout block
        ###########
        rv = b""

        ## Header
        text_size = len(text_section)
        block_size = 0x20 + text_size + len(offset_section)
        unknown = 0x01 # @TODO: Take the value from the actual game

        rv += struct.pack("<I", block_size)
        rv += struct.pack("<I", text_size)
        rv += struct.pack("<I", unknown)
        rv += struct.pack("IIIII", 0x00, 0x00, 0x00, 0x00, 0x00)
        rv += text_section
        rv += offset_section

        return rv


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

    elf_file.seek(0, os.SEEK_END)
    elfsize = elf_file.tell()

    #######
    ## Extract EXO.bin texts
    #######
    elf_file.seek(EXO_POINTERS)

    prev_block = None
    prev_block_val = 0

    text_bytes = 0
    free_bytes = 0

    while True:
        elf_pointer = elf_file.tell()

        exo_size = struct.unpack('<I', elf_file.read(4))[0]
        unknown = struct.unpack('<I', elf_file.read(4))[0]

        if exo_size == 0x00000000 or exo_size == 0xFFFFFFFF:
            continue

        if unknown != 0:
            # print(f"Unknown command at ELF address {elf_pointer:08X}")
            continue

        exo_pointer = struct.unpack('<I', elf_file.read(4))[0]
        zeros = struct.unpack('<I', elf_file.read(4))[0]
        
        if elf_pointer >= EXO_POINTERS_END:
            break
        if exo_pointer > 0x06000000 or exo_pointer < 0x04000000:
            continue
        
        ## Check the exo block
        exo_file.seek(exo_pointer)
        block = ExoScriptBlock()
        block.elf_address = elf_pointer
        block.unpack(exo_file)

        block_val = exo_pointer/2048
        if block_val != prev_block_val:
            print("Non consequtive block detected")

        if (block.text_size > 0):
            ## Print the data
            remaining_size_in_block = 2048 - exo_size%2048
            # Blocks: {exo_size/2048:0.1f} | 
            
            print_text = f"""
Exo: {exo_pointer:08X} |
Blocks: {exo_pointer/2048:0.0f} + {math.ceil(exo_size/2048):3.0f} |
Text bytes: {block.text_size:5d} |
Free bytes: {remaining_size_in_block:4d} |
Percentage Free: {100*(remaining_size_in_block/block.text_size):0.1f}%
""".replace("\n", " ")

            print(print_text)
        else:
            print_text = f"""
Exo: {exo_pointer:08X} |
Blocks: {exo_pointer/2048:0.0f} + {math.ceil(exo_size/2048):3.0f} |
Text bytes: {block.text_size:5d} |
Free bytes: {remaining_size_in_block:4d}
""".replace("\n", " ")
            
            print(print_text)
        
        text_bytes += block.text_size
        free_bytes += remaining_size_in_block


        prev_block_val = block_val + math.ceil(exo_size/2048)
        prev_block = block
    
    print(f"Text: {text_bytes} | Free: {free_bytes}")

