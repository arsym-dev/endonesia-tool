import struct
from typing import List
from PIL import Image
from io import BufferedReader

from endotool.utils import pad_to_nearest

def readUInt8(data, offset):
    return struct.unpack('<B', data[offset:offset+1])[0]

def readUInt16(data, offset):
    return struct.unpack('<H', data[offset:offset+2])[0]

def readUInt32(data, offset):
    return struct.unpack('<I', data[offset:offset+4])[0]

def readInt8(data, offset):
    return struct.unpack('<b', data[offset:offset+1])[0]

def readInt16(data, offset):
    return struct.unpack('<h', data[offset:offset+2])[0]

def readInt32(data, offset):
    return struct.unpack('<i', data[offset:offset+4])[0]

H3_un3_values = []

class PackedImageInfo:
    def __init__(self) -> None:
        self.image: Image = None
        self.animations: List[Animation] = []
        self.frame_image_data: List[FrameImageData] = []
        self.bitdepth: int = 0
        self.raw_data: bytes = b''
    
    def from_buffer(self, buffer: BufferedReader) -> None:
        offset_start = buffer.tell()
        header_size = struct.unpack('<I', buffer.read(4))[0]
        buffer.seek(-4, 1)
        data = buffer.read(header_size + 0x30)
        self.raw_data = data

        header_size = readUInt32(data, 0)
        img_data_offset_qqq = readUInt32(data, 4)

        num_frames = readUInt16(data, header_size + 0x00)
        num_animations = readUInt16(data, header_size + 0x02)
        offset_to_frames_header = readUInt32(data, header_size + 0x04)
        offset_to_animations_header = readUInt32(data, header_size + 0x08)
        offset_to_image = readUInt32(data, header_size + 0x0C)
        img_width = readUInt32(data, header_size + 0x10)
        img_height = readUInt32(data, header_size + 0x14)
        bitdepth = readUInt32(data, header_size + 0x18)
        self.bitdepth = bitdepth

        # header_size_img_specs = offset_to_frames_header - 8
        # header_size_frames = offset_to_animations_header - offset_to_frames_header
        # header_size_animations = header_size - offset_to_animations_header

        self.frame_image_data = []
        for i_f in range(num_frames):
            self.frame_image_data.append(FrameImageData())
            fid = self.frame_image_data[-1]
            fid.count = readUInt32(data, offset_to_frames_header + i_f*8 + 0x00)
            fid.frame_num = i_f

            offset_to_img_spec = readUInt32(data, offset_to_frames_header + i_f*8 + 0x04)
            size_of_img_spec = 32*fid.count + 4*int((fid.count + 3)/4)

            ## Create ImageSpecifications
            fid.img_specs = ImageSpecifications()
            img_spec = fid.img_specs
            img_spec.unknown1 = readInt16(data, offset_to_img_spec + 0x00)
            img_spec.unknown2 = readInt16(data, offset_to_img_spec + 0x02)
            img_spec.unknown3 = readInt16(data, offset_to_img_spec + 0x04)
            img_spec.crop_rect = Rect(
                left = readUInt16(data, offset_to_img_spec + 0x06),
                top = readUInt16(data, offset_to_img_spec + 0x08),
                right = readUInt16(data, offset_to_img_spec + 0x0A),
                bottom = readUInt16(data, offset_to_img_spec + 0x0C),
            )
            img_spec.offset = Vector2(
                x = readInt16(data, offset_to_img_spec + 0x0E),
                y = readInt16(data, offset_to_img_spec + 0x10),
            )
            img_spec.rotation = readInt16(data, offset_to_img_spec + 0x12)
            img_spec.scale = Vector2(
                x = readUInt16(data, offset_to_img_spec + 0x14),
                y = readUInt16(data, offset_to_img_spec + 0x16),
            )
            img_spec.unknown_remaining = data[offset_to_img_spec + 0x18 : offset_to_img_spec + size_of_img_spec]

        for i_a in range(num_animations):
            offset_animation = offset_to_animations_header + i_a*16
            self.animations.append(Animation())
            ani = self.animations[-1]
            num_frames = readUInt16(data, offset_animation + 0x00)
            ani.animation_duration = readUInt16(data, offset_animation + 0x02)
            offset_to_frame_data = readUInt32(data, offset_animation + 0x04)
            H3_un3 = readUInt32(data, offset_animation + 0x08)
            H3_offset_to_H3T3 = readUInt32(data, offset_animation + 0x0C)

            # if (H3_un3 != 0 or H3_offset_to_H3T3 != 0):
            if (H3_un3 != 0  and H3_un3 not in H3_un3_values):
                H3_un3_values.append(H3_un3)
                pass ## TODO: Implement
                ## raise Exception("Not implemented")
            
            for i_ftd in range(num_frames):
                frame_num = readUInt16(data, offset_to_frame_data + i_ftd*4 + 0x00)

                if frame_num == 0xFFFF:
                    ## TODO: I have no idea why this happens but it does.
                    ## I'm choosing to ignore it but that's probably wrong
                    continue

                ani.frame_timing_data.append(FrameTimingData())
                frame_timing_data = ani.frame_timing_data[-1]
                frame_timing_data.frame_duration = readUInt16(data, offset_to_frame_data + i_ftd*4 + 0x02)
                frame_timing_data.frame_num = frame_num # self.frame_image_data[frame_num]
                self.frame_image_data[frame_num].accessed += 1
        
        pass

    def serialize(self):
        return {
            'frame_image_data': [fid.serialize() for fid in self.frame_image_data],
            'animations': [a.serialize() for a in self.animations]
        }
    
    def deserialize(self, data):
        self.frame_image_data = []
        for datum in data['frame_image_data']:
            self.frame_image_data.append(FrameImageData())
            self.frame_image_data[-1].deserialize(datum)
        
        self.animations = []
        for datum in data['animations']:
            self.animations.append(Animation())
            self.frame_image_data[-1].deserialize(datum)

class Animation:
    def __init__(self) -> None:
        self.animation_duration: int = 0
        self.frame_timing_data: List['FrameTimingData'] = []
    
    def serialize(self):
        return {
            'animation_duration': self.animation_duration,
            'frame_timing_data': [ftd.serialize() for ftd in self.frame_timing_data]
        }

    def deserialize(self, data):
        self.animation_duration = data['animation_duration']
        self.frame_timing_data = []
        for datum in data['frame_timing_data']:
            self.frame_timing_data.append(FrameTimingData())
            self.frame_timing_data[-1].deserialize(datum)

class FrameTimingData:
    def __init__(self) -> None:
        self.frame_num: int
        self.frame_duration: int
    
    def serialize(self):
        return {
            'frame_num': self.frame_num,
            'frame_duration': self.frame_duration,
        }
    
    def deserialize(self, data):
        self.frame_num = data['frame_num']
        self.frame_duration = data['frame_duration']


class FrameImageData:
    def __init__(self) -> None:
        self.frame_num: int
        self.count: int # Don't know what to do if it's greater than 1
        self.img_specs: ImageSpecifications
        self.accessed = 0
    
    def serialize(self):
        return {
            'frame_num': self.frame_num,
            'count': self.count,
            'image_specifications': self.img_specs.serialize()
        }
    
    def deserialize(self, data):
        self.frame_num = data['frame_num']
        self.count = data['count']
        self.img_specs = ImageSpecifications()
        self.img_specs.deserialize(data['image_specifications'])

class ImageSpecifications:
    def __init__(self) -> None:
        self.unknown1: int
        self.unknown2: int
        self.unknown3: int
        self.crop_rect: Rect
        self.offset: Vector2
        self.rotation: int
        self.scale: Vector2
        self.unknown_remaining: bytes
    
    def serialize(self):
        return {
            'unknown1': self.unknown1,
            'unknown2': self.unknown2,
            'unknown3': self.unknown3,
            'crop_rect': self.crop_rect.serialize(),
            'offset': self.offset.serialize(),
            'rotation': self.rotation,
            'scale': self.scale.serialize(),
            'unknown_remaining': list(self.unknown_remaining)
        }

    def deserialize(self, data):
        self.unknown1 = data['unknown1']
        self.unknown2 = data['unknown2']
        self.unknown3 = data['unknown3']
        self.crop_rect = Rect()
        self.crop_rect.deserialize(data['crop_rect'])
        self.offset = Vector2()
        self.offset.deserialize(data['offset'])
        self.rotation = data['rotation']
        self.scale = Vector2()
        self.scale.deserialize(data['scale'])
        self.unknown_remaining = bytes(data['unknown_remaining'])

class Rect:
    def __init__(self, left: int, top: int, right: int, bottom: int) -> None:
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
    
    def serialize(self):
        return {
            'left': self.left,
            'top': self.top,
            'right': self.right,
            'bottom': self.bottom,
        }

    def deserialize(self, data):
        self.left = data['left']
        self.top = data['top']
        self.right = data['right']
        self.bottom = data['bottom']

class Vector2:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
    
    def serialize(self):
        return {
            'x': self.x,
            'y': self.y,
        }

    def deserialize(self, data):
        self.x = data['x']
        self.y = data['y']