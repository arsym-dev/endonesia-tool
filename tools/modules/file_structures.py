import struct
from typing import List
from io import TextIOWrapper

import jis208
from utils import pad_to_nearest


class ExoScriptTextEntry:
    item_num : int = 0
    offset : int = 0
    text : str = ""
    transform_ascii : bool = False

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
                 text_entries : List[ExoScriptTextEntry] = None,
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
        self.script_section : bytearray = b""
    
    @property
    def text_size(self):
        return self.offset_to_textoffsets - 0x20
    
    def fromBinary(self, exo_file : TextIOWrapper):
        if self.exo_address == 0:
            raise AttributeError("exo_address must be non-zero before calling unpack. Set the value in the block constructor.")
        
        exo_file.seek(self.exo_address)

        ## Grab the header data
        self.text_entries = []
        self.block_size = struct.unpack('<I', exo_file.read(4))[0]
        self.offset_to_textoffsets = struct.unpack('<I', exo_file.read(4))[0]
        self.unknown = struct.unpack('<I', exo_file.read(4))[0]

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
            exo_file.seek(self.exo_address + text_pointer)
            
            ## Only create entries for text inside the actual block
            ## This is because some "text" is in the script portion
            ## (eg. "PAD_OFF", "PAD_ON")
            if 0 < text_pointer < self.block_size:
                entry = ExoScriptTextEntry()
                entry.item_num = current_item
                entry.offset = current_pos
                entry.text = jis208.decode(exo_file)
                self.text_entries.append(entry)

            current_pos += 4
            current_item += 1
    
    def toBinary(self) -> bytes:
        ## Process the strings so they become valid EUC JP
        output_strings = []
        for s in self.text_entries:
            byte_string = jis208.stringToHex(s.text, transform_ascii=s.transform_ascii)
            output_strings.append(pad_to_nearest(byte_string))
        
        ## Get the length of each of these strings and create an offset,
        ## keeping in mind that the smallest offset is 0x20 to account for the header
        self.offsets = [0x20]
        for i in range(1, len(output_strings)):
            self.offsets.append(self.offsets[-1]+len(output_strings[i-1]))
        
        ## Reverse the string and offset lists and create each section
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
        
        ## Header
        text_size = len(text_section)
        block_size = 0x20 + text_size + len(offset_section)
        unknown = self.unknown

        rv = b""
        rv += struct.pack("<I", block_size)
        rv += struct.pack("<I", text_size)
        rv += struct.pack("<I", unknown)
        rv += struct.pack("IIIII", 0x00, 0x00, 0x00, 0x00, 0x00)

        ## Remaining sections
        rv += text_section
        rv += offset_section

        return rv