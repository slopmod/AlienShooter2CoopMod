"""Lossless reader for OLD's raw RES/MENU resources.

Coordinates are retained as stored, including editor viewport and origin.
The reader does not guess runtime anchors, animation frames or native flags.
It never loads the game, modifies its resources, or executes menu actions.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import struct


@dataclass(frozen=True)
class MenuResource:
    header: bytes
    sprite_header: bytes
    records: tuple[bytes, ...]  # Includes the final -1 sentinel.

    @classmethod
    def read(cls, data: bytes) -> 'MenuResource':
        if len(data) < 12 or data[:4] != b'RES ' or data[8:12] != b'MENU':
            raise ValueError('Expected RES/MENU container')
        if struct.unpack_from('<I', data, 4)[0] != len(data) - 8:
            raise ValueError('Menu container length mismatch')
        cursor, chunks = 12, []
        while cursor < len(data):
            if cursor + 8 > len(data):
                raise ValueError('Truncated menu chunk header')
            size = struct.unpack_from('<I', data, cursor + 4)[0]
            end = cursor + 8 + size
            if end > len(data):
                raise ValueError('Menu chunk exceeds container')
            chunks.append((data[cursor:cursor + 4], data[cursor + 8:end]))
            cursor = end
        if [tag for tag, _ in chunks] != [b'HEAD', b'SPR ']:
            raise ValueError('Unsupported menu chunk sequence')
        header, payload = chunks[0][1], chunks[1][1]
        if (len(header) != 36
                or struct.unpack_from('<4I', header) != (0x80000000, 0, 1, 20)
                or struct.unpack_from('<I', header, 16)[0] not in (0, 10, 18, 19)):
            raise ValueError('Unsupported menu header version')
        version = struct.unpack_from('<I', header, 16)[0]
        if len(payload) < 12 or struct.unpack_from('<2I', payload) != (0x80000000, 0):
            raise ValueError('Expected raw sprite block')
        count = struct.unpack_from('<I', payload, 8)[0]
        if not 1 <= count <= (len(payload) - 12) // 8:
            raise ValueError('Invalid menu sprite count')
        cursor, records = 12, []
        for index in range(count):
            if cursor + 4 > len(payload):
                raise ValueError('Truncated sprite length')
            size = struct.unpack_from('<I', payload, cursor)[0]
            cursor += 4
            end = cursor + size
            if end > len(payload):
                raise ValueError('Sprite exceeds block')
            record = payload[cursor:end]
            if index == count - 1:
                if record != b'\xff\xff\xff\xff':
                    raise ValueError('Missing sprite terminator')
            elif (len(record) < {0: 32, 10: 32, 18: 57, 19: 61}[version]
                    or version >= 18 and not record.endswith(b'\0')):
                raise ValueError('Unsupported sprite record')
            records.append(record)
            cursor = end
        if cursor != len(payload):
            raise ValueError('Trailing sprite data')
        result = cls(header, payload[:12], tuple(records))
        # Reject non-finite coordinates before consumers perform arithmetic.
        floats = list(struct.unpack_from('<4f' if version >= 18 else '<4i', header, 20))
        for record in records[:-1]:
            floats.extend(struct.unpack_from('<3i' if version == 0 else '<3f', record, 8))
            if version >= 18:
                floats.extend(struct.unpack_from('<3f', record, 36))
        if not all(math.isfinite(value) for value in floats):
            raise ValueError('Non-finite menu geometry')
        return result

    def encode(self) -> bytes:
        payload = self.sprite_header[:8] + struct.pack('<I', len(self.records))
        payload += b''.join(struct.pack('<I', len(r)) + r for r in self.records)
        body = b'MENUHEAD' + struct.pack('<I', len(self.header)) + self.header
        body += b'SPR ' + struct.pack('<I', len(payload)) + payload
        return b'RES ' + struct.pack('<I', len(body)) + body

    def describe(self) -> dict:
        version = struct.unpack_from('<I', self.header, 16)[0]
        width, height, origin_x, origin_y = struct.unpack_from(
            '<4f' if version >= 18 else '<4i', self.header, 20)
        sprites = []
        for record in self.records[:-1]:
            saved_id, vid = struct.unpack_from('<2I', record)
            x, y, z = struct.unpack_from('<3i' if version == 0 else '<3f', record, 8)
            strings = ['']
            if version >= 18:
                tail = record[60 if version == 19 else 56:]
                name, tail = tail.split(b'\0', 1)
                strings = [name.decode('cp1251')]
                if version == 18 and tail:
                    # v18 text properties follow the name; v19 moved them into
                    # the fixed record prefix. Do not mistake them for a caption.
                    tail = tail[4:]
                strings += tail.decode('cp1251').split('\0')[:-1]
            sprites.append(dict(
                saved_id=saved_id, vid=vid, name=strings[0], strings=strings[1:],
                stored_xyz=[x, y, z], stored_direction=struct.unpack_from('<I', record, 20)[0],
                scale_xyz=list(struct.unpack_from('<3f', record, 36)) if version >= 18 else None,
                # Keep all uninterpreted properties/tail available for review.
                record_hex=record.hex(),
                # Candidate projection only; see native-coordinate-check.json.
                centered_xy=[x - origin_x - width / 2,
                             y - z - origin_y - height / 2],
                record_sha256=hashlib.sha256(record).hexdigest(), byte_length=len(record)))
        return dict(format_version=struct.unpack_from('<I', self.header, 16)[0],
                    editor_viewport=[width, height], editor_origin=[origin_x, origin_y],
                    header_hex=self.header.hex(), sprite_count=len(sprites), sprites=sprites)
