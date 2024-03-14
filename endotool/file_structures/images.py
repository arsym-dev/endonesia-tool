# TODO: Make sure the GUI works well with 10216 (has animations with frame_num=-1)
# TODO: Clicking around and saving is causing fields to change. It's caused by self.update_data_typed()

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

def createUInt8(value):
    return struct.pack('<B', value)

def createUInt16(value):
    return struct.pack('<H', value)

def createUInt32(value):
    return struct.pack('<I', value)

def createInt8(value):
    return struct.pack('<b', value)

def createInt16(value):
    return struct.pack('<h', value)

def createInt32(value):
    return struct.pack('<i', value)

class PackedImageInfo:
    def __init__(self) -> None:
        self.image: Image = None
        self.animations: List[Animation] = []
        self.frame_image_data: List[FrameImageData] = []
        self.bitdepth: int = 0
        self.raw_data: bytes = b''
        self.image_width: int = 0
        self.image_height: int = 0

        self.offset_start: int = 0
        self.img_data_offset_qqq: int = 0
        self.offset_to_frames_header: int = 0
        self.offset_to_image_specifications: int = 0
        self.offset_to_animations_header: int = 0
        self.offset_to_image: int = 0
        self.offset_to_frame_data: int = 0
        self.bits: int = 16

    def from_buffer(self, buffer: BufferedReader) -> None:
        self.offset_start = buffer.tell()
        self.header_size = struct.unpack('<I', buffer.read(4))[0]
        buffer.seek(-4, 1)
        data = buffer.read(self.header_size + 0x30)
        self.raw_data = data

        self.header_size = readUInt32(data, 0)
        self.img_data_offset_qqq = readUInt32(data, 4)

        num_frames = readUInt16(data, self.header_size + 0x00)
        num_animations = readUInt16(data, self.header_size + 0x02)
        if num_animations > 0:
            self.bits = 16
            self.offset_to_frames_header = readUInt32(data, self.header_size + 0x04)
            self.offset_to_animations_header = readUInt32(data, self.header_size + 0x08)
            self.offset_to_image = readUInt32(data, self.header_size + 0x0C)
            self.image_width = readUInt32(data, self.header_size + 0x10)
            self.image_height = readUInt32(data, self.header_size + 0x14)
            self.bitdepth = readUInt32(data, self.header_size + 0x18)
        else:
            self.bits = 32
            num_animations = readUInt32(data, self.header_size + 0x04) # I have no idea why they do this, it's the dumbest thing ever
            self.offset_to_frames_header = readUInt32(data, self.header_size + 4 + 0x04)
            self.offset_to_animations_header = readUInt32(data, self.header_size + 4 + 0x08)
            self.offset_to_image = readUInt32(data, self.header_size + 4 + 0x0C)
            self.image_width = readUInt32(data, self.header_size + 4 + 0x10)
            self.image_height = readUInt32(data, self.header_size + 4 + 0x14)
            self.bitdepth = readUInt32(data, self.header_size + 4 + 0x18)

        # header_size_img_specs = offset_to_frames_header - 8
        # header_size_frames = offset_to_animations_header - offset_to_frames_header
        # header_size_animations = header_size - offset_to_animations_header

        self.frame_image_data = []
        for i_f in range(num_frames):
            self.frame_image_data.append(FrameImageData())
            fid = self.frame_image_data[-1]
            fid.count = readUInt32(data, self.offset_to_frames_header + i_f*8 + 0x00)
            fid.frame_num = i_f

            offset_to_img_spec = readUInt32(data, self.offset_to_frames_header + i_f*8 + 0x04)
            if (self.offset_to_image_specifications == 0) or (offset_to_img_spec < self.offset_to_image_specifications):
                self.offset_to_image_specifications = offset_to_img_spec

            if i_f < num_frames-1:
                offset_to_next_img_spec = readUInt32(data, self.offset_to_frames_header + (i_f+1)*8 + 0x04)
            else:
                offset_to_next_img_spec = self.offset_to_frames_header
            size_of_img_spec = offset_to_next_img_spec - offset_to_img_spec #32*fid.count + 8*int((fid.count + 3)/4)

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

        self.offset_to_frame_data = readUInt32(data, self.offset_to_animations_header + 0x04)

        for i_a in range(num_animations):
            offset_animation = self.offset_to_animations_header + i_a*16
            self.animations.append(Animation())
            anim = self.animations[-1]
            num_aniframes = readUInt16(data, offset_animation + 0x00)
            anim.animation_duration = readUInt16(data, offset_animation + 0x02)
            offset_to_frame_data = readUInt32(data, offset_animation + 0x04)
            num_unknown_transforms = readUInt32(data, offset_animation + 0x08)
            offset_to_transform = readUInt32(data, offset_animation + 0x0C)
            unknown_transforms = []

            ## CHECK: This is a weird exception we have to make. A "zero frame" animation has a single "-1" frame. It may have some transform though
            if num_aniframes == 0:
                num_aniframes = 1

            for idx in range(num_unknown_transforms):
                ## I'm not entirely sure what this section is. Each frame is 4 points that can be positive or negative values.
                ## If I had to guess, it's probably some kind of transform like shearing to give images a "swaying" animation
                tf = Vector4(
                    readInt16(data, offset_to_transform + idx*8 + 0x00),
                    readInt16(data, offset_to_transform + idx*8 + 0x02),
                    readInt16(data, offset_to_transform + idx*8 + 0x04),
                    readInt16(data, offset_to_transform + idx*8 + 0x06),
                )
                unknown_transforms.append(tf)


            for i_ftd in range(num_aniframes):
                if self.bits == 16:
                    ## 16 bit values
                    frame_num = readInt16(data, offset_to_frame_data + i_ftd*4 + 0x00)
                    frame_duration = readUInt16(data, offset_to_frame_data + i_ftd*4 + 0x02)
                else:
                    ## 32 bit values
                    frame_num = readInt32(data, offset_to_frame_data + i_ftd*8 + 0x00)
                    frame_duration = readUInt32(data, offset_to_frame_data + i_ftd*8 + 0x04)

                # if frame_num == 0xFFFF:
                #     ## I have no idea why this happens but it does.
                #     ## I'm choosing to ignore it but that's probably wrong
                #     continue

                # else:
                #     ani.frame_timing_data.append(FrameTimingData())
                #     frame_timing_data = ani.frame_timing_data[-1]
                #     frame_timing_data.frame_duration = frame_duration
                #     frame_timing_data.frame_num = frame_num # self.frame_image_data[frame_num]
                #     self.frame_image_data[frame_num].accessed += 1

                anim.frame_timing_data.append(FrameTimingData())
                frame_timing_data = anim.frame_timing_data[-1]
                frame_timing_data.frame_duration = frame_duration
                frame_timing_data.frame_num = frame_num # self.frame_image_data[frame_num]
                frame_timing_data.unknown_transforms = unknown_transforms

                # if frame_num == -1:
                #     ## I have no idea why this happens but it does. Frame_num is -1, so no image loaded
                #     pass
                # else:
                #     self.frame_image_data[frame_num].accessed += 1

    def rebuild(self) -> bytes:
        final_output = bytes()

        final_output += createUInt32(self.header_size)
        final_output += createUInt32(self.img_data_offset_qqq)

        while (self.offset_to_image_specifications > len(final_output)):
            final_output += createInt32(0)

        # if self.bits == 32:
        #     final_output += createInt32(0)
        #     final_output += createInt32(0)

        ############
        ## Pack the image specifications bytes
        ############
        byte_list_img_specs: List[bytes] = []

        for fid in self.frame_image_data:
            temp_bytes = bytes()
            specs: ImageSpecifications = fid.img_specs
            temp_bytes += createInt16(specs.unknown1)
            temp_bytes += createInt16(specs.unknown2)
            temp_bytes += createInt16(specs.unknown3)
            temp_bytes += createInt16(specs.crop_rect.left)
            temp_bytes += createInt16(specs.crop_rect.top)
            temp_bytes += createInt16(specs.crop_rect.right)
            temp_bytes += createInt16(specs.crop_rect.bottom)
            temp_bytes += createInt16(specs.offset.x)
            temp_bytes += createInt16(specs.offset.y)
            temp_bytes += createInt16(specs.rotation)
            temp_bytes += createInt16(specs.scale.x)
            temp_bytes += createInt16(specs.scale.y)
            temp_bytes += specs.unknown_remaining

            # if self.bits == 32:
            #     bytes_to_add = 16 - len(temp_bytes)%16
            #     if bytes_to_add != 16:
            #         temp_bytes += b'\x00'*bytes_to_add

            byte_list_img_specs.append(temp_bytes)

        for b in byte_list_img_specs:
            final_output += b

        ############
        ## Second Header
        ############
        output_second_header = bytes()
        offset = self.offset_to_image_specifications
        # if self.bits == 16:
        #     offset = 0x08
        # else:
        #     offset = 0x10

        for idx, fid in enumerate(self.frame_image_data):
            output_second_header += createInt32(fid.count)
            output_second_header += createInt32(offset)
            offset += len(byte_list_img_specs[idx])

        if self.bits == 32:
            bytes_to_add = 16 - len(output_second_header)%16
            if bytes_to_add != 16:
                output_second_header += b'\x00'*bytes_to_add

        final_output += output_second_header

        ############
        ## Animation timing data
        ############

        byte_list_frame_timing_data: List[bytes] = []
        byte_list_unknown_transforms: List[bytes] = []
        for idx_anim, anim in enumerate(self.animations):
            temp_bytes_timing = bytes()# TODO + createInt16(-1)
            if self.bits == 16:
                for idx_ftd, ftd in enumerate(anim.frame_timing_data):
                    temp_bytes_timing += createInt16(ftd.frame_num)
                    temp_bytes_timing += createInt16(ftd.frame_duration)

                if len(anim.frame_timing_data)%2 == 1:
                    ## Pad so it's 16 bits long
                    temp_bytes_timing += createInt32(0)
            else:
                for idx_ftd, ftd in enumerate(anim.frame_timing_data):
                    temp_bytes_timing += createInt32(ftd.frame_num)
                    temp_bytes_timing += createInt32(ftd.frame_duration)

                if len(anim.frame_timing_data)%2 == 1:
                    ## Pad so it's 32 bits long
                    temp_bytes_timing += createInt32(0) + createInt32(0)

            byte_list_frame_timing_data.append(temp_bytes_timing)

            ## Unknown transforms
            temp_bytes_transform = bytes()
            if len(anim.frame_timing_data) > 0:
                ftd = anim.frame_timing_data[0]

                # for idx_ftd, ftd in enumerate(anim.frame_timing_data):
                for ut in ftd.unknown_transforms:
                    temp_bytes_transform += createInt16(ut.x) + createInt16(ut.y) + createInt16(ut.z) + createInt16(ut.w)
                if len(temp_bytes_transform) > 0:
                    byte_list_unknown_transforms.append(temp_bytes_transform)

        offset_unknown_transforms = len(output_second_header) #sum([len(x) for x in byte_list_frame_timing_data])

        for b in byte_list_frame_timing_data:
            offset_unknown_transforms += len(b)
            final_output += b
        for b in byte_list_unknown_transforms:
            final_output += b

        ############
        ## Animations data
        ############
        offset_frame_timing_data = 0

        idx_ut = 0
        for idx_anim, anim in enumerate(self.animations):
            if len(anim.frame_timing_data) == 1 and anim.frame_timing_data[-1].frame_num == -1:
                num_aniframes = 0
            else:
                num_aniframes = len(anim.frame_timing_data)

            final_output += createInt16(num_aniframes)
            final_output += createInt16(anim.animation_duration)
            final_output += createInt32(self.offset_to_frame_data + offset_frame_timing_data)

            if self.bits == 16:
                offset_frame_timing_data += 0x08 * int((len(anim.frame_timing_data)+1)/2)
            else:
                offset_frame_timing_data += 0x10 * int((len(anim.frame_timing_data)+1)/2)

            ## Handle Unknown transform
            num_ut = 0
            if len(anim.frame_timing_data) > 0:
                ftd = anim.frame_timing_data[0]
                # for idx_ftd, ftd in enumerate(anim.frame_timing_data):
                num_ut += len(ftd.unknown_transforms)

            final_output += createInt32(num_ut)
            if num_ut == 0:
                final_output += createInt32(0)
            else:
                final_output += createInt32(self.offset_to_frames_header + offset_unknown_transforms)
                ut = byte_list_unknown_transforms[idx_ut]
                offset_unknown_transforms += len(ut)
                idx_ut += 1

        num_frames = createInt16(len(self.frame_image_data))
        if self.bits == 16:
            num_animations = createInt16(len(self.animations))
        else:
            num_animations = createInt16(0) + createInt32(len(self.animations))

        final_output += createInt16(len(self.frame_image_data))
        final_output += num_animations
        final_output += createInt32(self.offset_to_frames_header) #Offset to frame headers
        final_output += createInt32(self.offset_to_animations_header) #Offset to displayable headers
        final_output += createInt32(self.offset_to_image) #Offset to img data
        final_output += createUInt32(self.image_width)
        final_output += createUInt32(self.image_height)
        final_output += createUInt32(self.bitdepth)

        return final_output


    def serialize(self):
        return {
            'header_size': self.header_size,
            'header_offset': {
                'offset_start': self.offset_start,
                'img_data_offset_qqq': self.img_data_offset_qqq,
                'offset_to_frames_header': self.offset_to_frames_header,
                'offset_to_image_specifications': self.offset_to_image_specifications,
                'offset_to_animations_header': self.offset_to_animations_header,
                'offset_to_image': self.offset_to_image,
                'offset_to_frame_data': self.offset_to_frame_data,
            },
            'bits': self.bits,
            'bitdepth': self.bitdepth,
            'width': self.image_width,
            'height': self.image_height,
            'frame_image_data': [fid.serialize() for fid in self.frame_image_data],
            'animations': [a.serialize() for a in self.animations]
        }


    def deserialize(self, data):
        self.header_size = data['header_size']
        self.offset_start = data['header_offset']['offset_start']
        self.img_data_offset_qqq = data['header_offset']['img_data_offset_qqq']
        self.offset_to_frames_header = data['header_offset']['offset_to_frames_header']
        self.offset_to_image_specifications = data['header_offset']['offset_to_image_specifications']
        self.offset_to_animations_header = data['header_offset']['offset_to_animations_header']
        self.offset_to_image = data['header_offset']['offset_to_image']
        self.offset_to_frame_data = data['header_offset']['offset_to_frame_data']
        self.bits = data['bits']
        self.image_width = data['width']
        self.image_height = data['height']
        self.bitdepth = data['bitdepth']

        self.frame_image_data = []
        for datum in data['frame_image_data']:
            self.frame_image_data.append(FrameImageData())
            self.frame_image_data[-1].deserialize(datum)

        self.animations = []
        for datum in data['animations']:
            self.animations.append(Animation())
            self.animations[-1].deserialize(datum)


class Animation:
    def __init__(self) -> None:
        self.animation_duration: int = 0
        self.frame_timing_data: List['FrameTimingData'] = []

    def serialize(self):
        # self.animation_duration = sum([ftd.frame_duration for ftd in self.frame_timing_data])
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
        self.unknown_transforms: List[Vector4] = []

    def serialize(self):
        rv = {
            'frame_num': self.frame_num,
            'frame_duration': self.frame_duration,
        }
        if len(self.unknown_transforms) > 0:
            rv['unknown_transforms'] = [ut.serialize() for ut in self.unknown_transforms]

        return rv

    def deserialize(self, data):
        self.frame_num = data['frame_num']
        self.frame_duration = data['frame_duration']
        self.unknown_transforms = []
        if 'unknown_transforms' in data:
            for datum in data['unknown_transforms']:
                self.unknown_transforms.append(Vector4())
                self.unknown_transforms[-1].deserialize(datum)


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
            'crop_rect': self.crop_rect.serialize(),
            'offset': self.offset.serialize(),
            'rotation': self.rotation,
            'scale': self.scale.serialize(),
            'unknown1': self.unknown1,
            'unknown2': self.unknown2,
            'unknown3': self.unknown3,
            'unknown_remaining': self.unknown_remaining.hex()
            # 'unknown_remaining': list(self.unknown_remaining)
        }

    def deserialize(self, data):
        self.crop_rect = Rect()
        self.crop_rect.deserialize(data['crop_rect'])
        self.offset = Vector2()
        self.offset.deserialize(data['offset'])
        self.rotation = data['rotation']
        self.scale = Vector2()
        self.scale.deserialize(data['scale'])
        self.unknown1 = data['unknown1']
        self.unknown2 = data['unknown2']
        self.unknown3 = data['unknown3']
        self.unknown_remaining = bytes.fromhex(data['unknown_remaining'])
        # self.unknown_remaining = bytes(data['unknown_remaining'])

class Rect:
    def __init__(self, left: int = 0, top: int = 0, right: int = 0, bottom: int = 0) -> None:
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
    def __init__(self, x: int = 0, y: int = 0) -> None:
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


class Vector4:
    def __init__(self, x: int = 0, y: int = 0, z: int = 0, w: int = 0, ) -> None:
        self.x = x
        self.y = y
        self.z = z
        self.w = w

    def serialize(self):
        return [self.x, self.y, self.z, self.w]

    def deserialize(self, data):
        self.x, self.y, self.z, self.w = data