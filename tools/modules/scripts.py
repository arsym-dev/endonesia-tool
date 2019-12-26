import struct
import os
import io
import csv
import sys
import jis208
from utils import read_in_chunks, csv_find

ELF_ENUM = 'ELF'
EXO_ENUM = 'EXO'
RESERVED = 0x33D070
EXO_POINTERS = 0x2C8270
ELF_POINTERS = [
    {'pointer': 0x3094C0
        , 'size': 2928}
    , {'pointer': 0x310780
        , 'size': 752}
    , {'pointer': 0x313310
        , 'size': 1000}
    , {'pointer': 0x3497B8
        , 'size': 12}
    , {'pointer': 0x330AD0
        , 'size': 760}]
ELF_OFFSET = -0x163F000

EXO_STRIDE = 0x800

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

    csvexists = False
    try:
        if os.path.exists(output):
            csvfile = open(output, 'r')
            reader = csv.reader(x.replace('\0', '') for x in csvfile)
            csvref = [r for r in reader]
            csvfile.close()
            csvexists = True
        else:
            overwite = True
        output_file = open(output, 'w')
        writer = csv.writer(output_file)
    except IOError as e:
        print(e, file = sys.stderr)
        return 2

    elf_file.seek(0, os.SEEK_END)
    elfsize = elf_file.tell()

    # Extract ELF texts
    for i in ELF_POINTERS:
        currentpos = i['pointer']
        currentsize = 0
        while currentsize < i['size']:
            elf_file.seek(currentpos)
            row = [currentpos]
            pointer = struct.unpack('<I', elf_file.read(4))[0] + ELF_OFFSET
            row.append(pointer)
            row.append(ELF_ENUM)
            csvindex = csv_find(pointer = currentpos, csv = csvref) if csvexists else -1
            currentpos = elf_file.tell()
            currentsize += 4

            if pointer < 0x0 or pointer >= elfsize or (not overwrite and csvindex >= 0):
                # not a valid pointer
                continue

            elf_file.seek(pointer)

            text = decode(elf_file)
            if text:
                row.append(text)

                if csvexists:
                    if csvindex >= 0:
                        row.append(csvref[csvindex][4])
                        csvref[csvindex] = row
                    else:
                        row.append(' ')
                        csvref.append(row)
                else:
                    row.append(' ')
                    writer.writerow(row)

    #Extract exo.bin texts
    elf_file.seek(EXO_POINTERS)

    while True:
        elfpointer = elf_file.tell()
        pointer = struct.unpack('<I', elf_file.read(4))[0]
        if pointer == 0x0:
            break
        elf_file.seek(0xC, 1)

        exo_file.seek(pointer)
        blocksize = struct.unpack('<I', exo_file.read(4))[0]
        textsize = struct.unpack('<I', exo_file.read(4))[0]

        exo_file.seek(textsize - 0x8, 1)
        currentpos = exo_file.tell()
        currentsize = 0

        while currentsize < blocksize - textsize:
            exo_file.seek(currentpos)
            textpointer = struct.unpack('<I', exo_file.read(4))[0]
            exo_file.seek(pointer + textpointer)
            char = struct.unpack('>H', exo_file.read(2))[0]
            row = [elfpointer, currentpos - pointer, EXO_ENUM]
            csvindex = csv_find(pointer = elfpointer, text = currentpos - pointer, csv = csvref) if csvexists else -1

            currentpos += 4
            currentsize += 4
            if not overwrite and csvindex >= 0:
                break
            if jis208.validate(char):
                row.append(jis208.convertToString(char) + decode(exo_file))

                if csvexists:
                    if csvindex >= 0:
                        row.append(csvref[csvindex][4])
                        csvref[csvindex] = row
                    else:
                        row.append(' ')
                        csvref.append(row)
                else:
                    row.append(' ')
                    writer.writerow(row)

    if csvexists:
        for row in csvref:
            writer.writerow(row)

def pack(input, elf, exo):
    try:
        csvfile = open(input, 'r')
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

    csvref = csv.reader(x.replace('\0', '') for x in csvfile)

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

    for row in csvref:
        text = row[3] if not row[4] or row[4] == ' ' else row[4]
        required_size = hex_length(text)
        if row[2] == ELF_ENUM:
            elf_file.seek(int(row[1]))
            available_size = string_size(elf_file)
            if required_size > available_size:
                elf_file.seek(reserved_pointer)
                if not is_empty(elf_file, required_size):
                    print('Not enough reserved space left in the ELF file.')
                    return 2
                elf_file.seek(int(row[0]))
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
            elf_file.seek(int(row[0]))
            pointer = struct.unpack('<I', elf_file.read(4))[0]
            pointer_index = exo_pointers.index(pointer)

            exo_buffer.seek(pointer - exo_offset)
            exo_newbuffer = io.BytesIO()
            blocksize = exo_pointers[pointer_index + 1] - exo_pointers[pointer_index] if pointer_index < len(exo_pointers) else original_exo_size - exo_pointers[pointer_index]
            for piece in read_in_chunks(exo_buffer, size = blocksize):
                exo_newbuffer.write(piece)

            exo_newbuffer.seek(0)
            length = struct.unpack('<I', exo_newbuffer.read(4))[0]
            content_length = struct.unpack('<I', exo_newbuffer.read(4))[0]
            exo_newbuffer.seek(int(row[1]))
            textpos = struct.unpack('<I', exo_newbuffer.read(4))[0]
            exo_newbuffer.seek(textpos)
            print(hex(textpos), length, content_length, row[1], row[0], hex(int(row[1])), hex(int(row[0])))
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
