"""Bounded readers for the original RES/MAP sprite and action-stack format."""
from __future__ import annotations
import hashlib
import math
from pathlib import Path
import re
import struct


def u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError("Truncated 32-bit map field")
    return struct.unpack_from("<I", data, offset)[0]

def chunks(data: bytes):
    # Several supplied old campaign maps understate the outer RES length by
    # one byte. Inner chunk/record bounds still have to cover the exact file.
    if data[:4] != b"RES " or data[8:12] != b"MAP " or u32(data, 4) not in (len(data) - 8, len(data) - 9):
        raise ValueError("Unsupported RES/MAP container")
    cursor = 12
    while cursor < len(data):
        # The one-byte difference is an uncounted NUL before PLAY in those
        # supplied files, after the complete SPRD sentinel record.
        if data[cursor:cursor + 5] == b"\0PLAY" and u32(data, 4) == len(data) - 9:
            cursor += 1
        size = u32(data, cursor + 4)
        end = cursor + 8 + size
        if end > len(data):
            raise ValueError("Chunk extends beyond map")
        yield data[cursor:cursor + 4], cursor, data[cursor + 8:end]
        cursor = end

def records(payload: bytes, source_offset: int):
    if u32(payload, 0) != 0x80000000 or u32(payload, 4) != 0:
        raise ValueError("Only the verified raw record layout is supported")
    count = u32(payload, 8)
    if count > 100000:
        raise ValueError("Unreasonable map record count")
    cursor = 12
    for _ in range(count):
        size = u32(payload, cursor)
        start = cursor + 4
        if start + size > len(payload):
            raise ValueError("Record extends beyond chunk")
        yield source_offset + start, payload[start:start + size]
        cursor = start + size
    if cursor != len(payload):
        raise ValueError("Trailing bytes after chunk records")

def action_names(export_path: Path) -> dict[int, str]:
    text = export_path.read_text("cp1251")
    return {int(number): name for name, number in
            re.findall(r"^#define\s+(ACT_\w+)\s+(\d+)\b", text, re.MULTILINE)}

def parse_map(path: Path, export_path: Path | None = None) -> dict:
    path = Path(path)
    data = path.read_bytes()
    names = action_names(Path(export_path) if export_path is not None else path.parent / "EXPORT.LGC")
    found = {tag: (offset, payload) for tag, offset, payload in chunks(data)}
    if b"SPR " not in found or b"SPRD" not in found:
        raise ValueError("Map has no SPR/SPRD pair")
    sprites = {}
    sprite_offset, sprite_payload = found[b"SPR "]
    blocks = list(records(sprite_payload, sprite_offset + 8))
    if len(blocks) != 1:
        raise ValueError("Expected one packed sprite-record block")
    block_offset, block = blocks[0]
    if len(block) < 4 or block[-4:] != b"\xff\xff\xff\xff" or (len(block) - 4) % 48:
        raise ValueError("Unsupported packed sprite layout")
    for offset in range(0, len(block) - 4, 48):
        saved_id, vid, x, y, z, direction, animation = struct.unpack_from("<IIfffII", block, offset)
        if saved_id in sprites or not all(math.isfinite(value) for value in (x, y, z)):
            raise ValueError("Duplicate saved ID or nonfinite coordinate")
        sprites[saved_id] = {
            "saved_id": hex(saved_id), "sprite_offset": hex(block_offset + offset),
            "vid": vid, "x": x, "y": y, "z": z,
            "direction": direction, "animation": animation,
        }
    detail_offset, detail_payload = found[b"SPRD"]
    detailed = set()
    for offset, record in records(detail_payload, detail_offset + 8):
        if record == b"\xff\xff\xff\xff":
            continue
        saved_id = u32(record, 0)
        if saved_id not in sprites or saved_id in detailed:
            raise ValueError("Unmatched or duplicate detail record")
        detailed.add(saved_id)
        sprite = sprites[saved_id]
        sprite["detail_offset"] = hex(offset - 4)
        # The second field has not been interpreted; retain it for diagnostics.
        sprite["detail_field_4"] = u32(record, 4)
        stack_count = u32(record, 8)
        if stack_count > 64:
            raise ValueError("Unreasonable action-stack count")
        cursor = 12
        stacks = []
        for _ in range(stack_count):
            count = u32(record, cursor)
            cursor += 4
            if count > 65536 or cursor + 16 * count > len(record):
                raise ValueError("Action stack extends beyond detail record")
            commands = []
            for _ in range(count):
                opcode, a, b, c = struct.unpack_from("<4i", record, cursor)
                commands.append({"offset": hex(offset + cursor), "opcode": opcode,
                                 "name": names.get(opcode), "args": [a, b, c]})
                cursor += 16
            stacks.append(commands)
        sprite["stacks"] = stacks
        property_count = u32(record, cursor)
        cursor += 4
        if property_count > 65536 or cursor + 4 * property_count > len(record):
            raise ValueError("Property list extends beyond detail record")
        sprite["raw_properties"] = list(struct.unpack_from("<" + "I" * property_count, record, cursor))
        cursor += 4 * property_count
        tail = record[cursor:]
        if tail.endswith(b"\0") and b"\0" not in tail[:-1]:
            sprite["label"] = tail[:-1].decode("cp1251", errors="replace")
        else:
            # Two Level_01 special records have additional opaque binary data.
            # Do not mistake it for a name or silently interpret it as script.
            sprite["label"] = None
            sprite["opaque_tail_bytes"] = len(tail)
    if detailed != sprites.keys():
        raise ValueError("Some packed sprites have no detail record")
    values = list(sprites.values())
    return {
        "file": str(path.resolve()), "sha256": hashlib.sha256(data).hexdigest(),
        "sprite_count": len(values),
        "scripted_count": sum(any(sprite["stacks"]) for sprite in values),
        "command_order": "Stored stack order. Execute last entry first; verify effects in the native runtime.",
        "sprites": values,
    }
