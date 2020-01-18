import math
import sys
from utils import tooldir
import os

TABLE_OFFSET = 0xA1

class TBL:
    tbl = {}
    PACK = os.path.join(tooldir, '..', 'assets', 'pack.tbl')

    def __init__(self, filename):
        try:
            tbl_file = open(filename, 'r')
        except IOError as e:
            print(e, file = sys.stderr)
            return False

        for line in tbl_file:
            parts = line.split('=')

            char = parts[0].strip()
            index = int(parts[1].strip(), 16)

            self.tbl[index] = char

        tbl_file.close()

    def index(self, char):
        keys = list(self.tbl.keys())
        values = list(self.tbl.values())
        return keys[values.index(char)] if char in values else -1

    def pos(self, char):
        index = self.index(char)
        if index >= 0:
            lead = index >> 8
            bite = index % 0x100
            return (lead - TABLE_OFFSET) * 94 + (bite - TABLE_OFFSET) if index >= 0xA1A1 else -1

    def char(self, index):
        return self.tbl[index] if index < len(self.tbl) else False
