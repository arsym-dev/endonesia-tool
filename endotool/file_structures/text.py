import struct
from typing import List
from io import TextIOWrapper
import os

from endotool import jis208
from endotool.utils import pad_to_nearest


class TextEntry:
    def __init__(self) -> None:
        self.elf_address : int = 0
        self.item_num : int = 0
        self.text_address : int = 0
        self.text : str = ""
        self.transform_ascii : bool = False
        
        self.connected_entries : List['TextEntry'] = []

    @property
    def primary_entry(self):
        return self.connected_entries[0]

    @property
    def is_duplicate(self):
        return self.primary_entry != self
    
    @property
    def byte_string(self) -> bytes:
        rv = jis208.stringToHex(self.text, transform_ascii=self.transform_ascii)
        ## Make sure the string is null-terminated, then pad it
        # return rv + bytes(1)
        return pad_to_nearest(rv + bytes(1), k=8)

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
                 text_entries : List[TextEntry] = None,
                 exo_size : int = 0,
                 elf_address : int = 0,
                 exo_address : int = 0) -> None:
        
        if text_entries is None:
            self.text_entries = []
        else:
            self.text_entries = text_entries

        ## ELF data
        ## <exo_size> <zeros> <elf_pointer> <zeros>
        self.exo_size : int = exo_size # The size of the EXO block according to the ELF
        self.elf_address : int = elf_address # The address in the ELF file. Contains the value of exo_address
        self.exo_address : int = exo_address # The address of this block in the EXO file

        ## EXO block data
        self.block_size : int = 0
        self.offset_to_textoffsets : int = 0
        self.unknown : int = 0
        self.offset_section : bytes = b""
        self.script_section : bytes = b""
    
    @property
    def text_size(self):
        return self.offset_to_textoffsets - 0x20
    
    def fromBinary(self, exo_file : TextIOWrapper):
        if self.exo_address == 0:
            raise AttributeError("exo_address must be non-zero before calling unpack. Set the value in the block constructor.")
        
        exo_file.seek(self.exo_address)

        ## Grab the header data
        self.text_entries : List[TextEntry] = []
        self.block_size = struct.unpack('<I', exo_file.read(4))[0]
        self.offset_to_textoffsets = struct.unpack('<I', exo_file.read(4))[0]
        self.unknown = struct.unpack('<I', exo_file.read(4))[0]

        ## Grab the offset data
        exo_file.seek(self.exo_address + self.offset_to_textoffsets)
        self.offset_section = exo_file.read(self.block_size - self.offset_to_textoffsets)

        ## Grab the script data
        exo_file.seek(self.exo_address + self.block_size)
        self.script_section = exo_file.read(self.exo_size - self.block_size)

        ## Grab the text data
        exo_file.seek(self.exo_address + self.offset_to_textoffsets)
        current_pos = exo_file.tell()
        current_item = 0

        while current_item < (self.block_size - self.offset_to_textoffsets)/4:
            exo_file.seek(current_pos)
            text_pointer = struct.unpack('<I', exo_file.read(4))[0]
            if text_pointer == 0:
                break
            
            ## Only create entries for text inside the actual block
            ## This is because some "text" is in the script portion
            ## (eg. "PAD_OFF", "PAD_ON")
            if 0 < text_pointer < self.block_size:
                entry = TextEntry()
                entry.item_num = current_item
                entry.text_address = text_pointer #current_pos - self.exo_address

                ## Make sure this entry wasn't already found before (pointing to same location)
                found_entry : TextEntry = None
                for entry2 in self.text_entries:
                    if entry.text_address == entry2.text_address:
                        found_entry = entry2
                        break

                if found_entry is None:
                    exo_file.seek(self.exo_address + text_pointer)
                    entry.text = jis208.decode(exo_file)
                    entry.connected_entries.append(entry)
                    self.text_entries.append(entry)
                else:
                    entry.connected_entries = found_entry.connected_entries
                    entry.connected_entries.append(entry)
                    self.text_entries.append(entry)

            current_pos += 4
            current_item += 1
        pass
    
    def toBinary(self) -> bytes:
        ## Create the primary text section as well as the
        ## secondary text section that's appended to the end
        ## of the block if it doesn't fit in the normal block
        text_section = b""
        text_section2 = b""
        is_primary_section = True
        prev_offset = 0x20

        for entry in self.text_entries[::-1]: # Process in reverse order
            if entry.is_duplicate:
                continue

            byte_string = entry.byte_string

            ## Make sure the text fits in the primary text area
            if is_primary_section:
                if len(text_section) + len(byte_string) <= self.text_size:
                    text_section += byte_string
                else:
                    ## Set up the secondary text section
                    is_primary_section = False
                    prev_offset = self.exo_size
                    text_section2 += byte_string
            
            else:
                text_section2 += byte_string
            
            entry.text_address = prev_offset
            prev_offset += len(entry.byte_string)

        ## Modify the offset section
        ## The idea is to preserve any weird references in the original
        ## that point to something in the script section
        for entry in self.text_entries:
            idx = entry.item_num*4

            self.offset_section = self.offset_section[:idx] + \
                                  struct.pack("<I", entry.primary_entry.text_address) + \
                                  self.offset_section[idx+4:]
        
        ###########
        ## Finally, write the output block
        ###########
        
        ## Header
        rv = b""
        rv += struct.pack("<I", self.block_size)
        rv += struct.pack("<I", self.offset_to_textoffsets)
        rv += struct.pack("<I", self.unknown)
        rv += struct.pack("IIIII", 0x00, 0x00, 0x00, 0x00, 0x00)

        ## Remaining sections
        if self.text_size > 0:
            rv += pad_to_nearest(text_section, k=self.text_size)
        rv += self.offset_section
        rv += self.script_section
        rv += pad_to_nearest(text_section2, k=16)

        ## Finally pad out the end a bit if needed
        self.exo_size = len(rv)
        rv = pad_to_nearest(rv, k=2048)

        return rv

class ElfTextStringBlock:
    def __init__(self, offset=0, end=0) -> None:
        self.offset : int = offset
        self.size : int = end-offset
        self.data : bytes = b""
    
    def canFit(self, byte_string: bytes):
        return len(self.data + byte_string) <= self.size
    
    def addByteString(self, byte_string: bytes) -> int:
        ptr = self.offset + len(self.data)
        self.data += byte_string
        return ptr

    def getData(self):
        return pad_to_nearest(self.data, self.size)

class ElfTextManager:
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

    ## @TODO: Make sure there are no other references to anything in these blocks
    ## @TODO: There's text at 0x2f8fa8 and below. Seems like item text
    def __init__(self) -> None:
        self.string_blocks : List[ElfTextStringBlock] = [
            ElfTextStringBlock(0x00343410, 0x00348330),
            ElfTextStringBlock(0x00348a20, 0x00348B00),
            ElfTextStringBlock(0x00348c10, 0x003492a8),
            ElfTextStringBlock(0x00349788, 0x003497C8),
            ElfTextStringBlock(0x00349d68, 0x0034A730),
            ElfTextStringBlock(0x0034A748, 0x0034A7E0),
            ElfTextStringBlock(0x0034dfa0, 0x0034DFF0),
            ElfTextStringBlock(0x0034e028, 0x0034E080),
            ElfTextStringBlock(0x0034E0C8, 0x0034E0E8),
            ElfTextStringBlock(0x0034e1a0, 0x0034E1B0),
            ElfTextStringBlock(0x0030A050, 0x0030F170), # free block of nulls I found. 20768 bytes
            # for some reason the block of text at 0x0034a730 isn't referenced
        ]

        self.text_entries : List[TextEntry] = []
    
    def readFromFile(self, elf_file : TextIOWrapper):
        elf_file.seek(0, os.SEEK_END)
        elfsize = elf_file.tell()

        for i in self.ELF_POINTERS:
            elf_pointer = i['pointer']
            current_pos = elf_pointer
            current_item = 0
            while current_item*4 < i['size']:
                elf_file.seek(current_pos)
                text_pointer = struct.unpack('<I', elf_file.read(4))[0] + self.ELF_OFFSET
                current_pos = elf_file.tell()
                current_item += 1

                if text_pointer < 0x0 or text_pointer >= elfsize:
                    # not a valid pointer
                    continue

                elf_file.seek(text_pointer)
                text = jis208.decode(elf_file)

                entry = TextEntry()
                entry.elf_address = elf_pointer
                entry.item_num = current_item-1
                entry.text_address = text_pointer
                entry.text = text

                self.text_entries.append(entry)

    def writeToFile(self, elf_file : TextIOWrapper):
        curr_string_block_idx = 0
        
        ## Find a space for each line of text and rite it in a buffer
        for entry in self.text_entries:
            byte_string = entry.byte_string

            while True:
                if curr_string_block_idx >= len(self.string_blocks):
                    raise Exception("Not enough space to rite ELF strings. Locate more null blocks to use and add them to string_blocks.")
                
                string_block = self.string_blocks[curr_string_block_idx]
                if string_block.canFit(byte_string):
                    text_pointer = string_block.addByteString(byte_string)
                    entry.text_address = text_pointer
                    break
                else:
                    curr_string_block_idx += 1
        
        ## Write the buffers to the file
        for entry in self.text_entries:
            elf_file.seek(entry.elf_address + 4*entry.item_num)
            elf_file.write(struct.pack("<I", entry.text_address - self.ELF_OFFSET))
        
        for block in self.string_blocks:
            elf_file.seek(block.offset)
            elf_file.write(block.getData())