"""Guarded, local-only resource import for the two Reloaded road maps.

No source game is modified and no game resource is embedded in this module.
The returned bytes belong in a disposable OLD runtime. Existing OLD object,
weapon, constant, sound and visual records remain byte-identical. A private
road VID preserves Reloaded's eight directions without changing OLD roads.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct

from tools.map_format import parse_map, records


FEATURE = 'old-reloaded-road-assets-v1'
OLD_OBJECTS_SHA256 = '988fdf676ad310791e59598076424ec13f31d7da6a76e4edcf4413a2dac26ade'
RELOADED_OBJECTS_SHA256 = '892eecb4eeb77d696099bcf8b2871e8e002fd6d8392403bc19d26af99149bf23'
ROAD_ALIAS = (1500, 3900)

# The body VID3100 transforms into VID3101 when destroyed. Both definitions
# are needed even though only the intact car is placed in the source maps.
# Values: source VID, graphics path, complete unmodified graphics SHA-256.
ASSETS = (
    (636, 'Vid/636.vid', '36d97568ffa7b6e77b7ab6a04a90b8a11c04cf9d7ee2bb1dfd82067a9b3fcb90'),
    (1159, 'Vid/1157.vid', '193f132a98c3a6c291ca4aef2ab56a6e3735bbfa16af85c7113a55fb88c81e92'),
    (1501, 'Vid/1501.vid', '19f6eb9652bf5f83c6421c70714ea4b1c4df8b4cc185c3a227c75496c2a300bd'),
    (3100, 'Vid/3100.vid', '06608201f292fb95c18a739d02a0febd798b2c9531e3048944ba204926048528'),
    (3101, 'Vid/3101.vid', '374d1fbaa5341a7c16094217df4aa825961d6c4cf8d3bbc06fe0530e575e65bd'),
    (3605, 'Vid/3605.vid', '02292212338f2f3a912a58cebdfb96a9fd4846a30bb6fcb91af62a0e8e11f8bd'),
    (3606, 'Vid/3606.vid', '47c4f0408d17185021468e6d0621a9774bfc497c6c8747d7c69752e5dbc7f74a'),
    (3607, 'Vid/3607.vid', 'a339ea69277278345fb5949fef1a9366608f58b3f99efdcbfd7abf890c9585b5'),
    (3608, 'Vid/3608.vid', 'aa155ac3942a307af43b60d636644c5a7f841c09490386b8bf583a4b8a1074ed'),
    (3610, 'Vid/3610.vid', 'b810ba2ce585bbac444922cf78ab0d90e9fac783920fdb78449cc47a1c853511'),
    (3615, 'Vid/3615.vid', '42be033b69b5980dcedf11b14ba506c87da6147247509c8351ad33a2d6c31fbc'),
    (3616, 'Vid/3616.vid', '0557f40065a8e75f76626ef4d6449e9247e8f9d301f9ce755743a14144faaa4e'),
    (3617, 'Vid/3617.vid', '3589dec6e466680c97180c08f5659c414925746cb4decc89707253f503a32ab0'),
    (3618, 'Vid/3618.vid', 'c71d98011059814587f90310dad16df0198fb93c60d8188e8bfe65c5e8a8ba44'),
    (3619, 'Vid/3619.vid', '8e5831189fa6d16120c9d42a59804ecc52e3a3d464d70868cf77c36f52ca10eb'),
    (3621, 'Vid/3621.vid', '00fd5f7e44f4b3a229db2126807a2f9e0af321a9935bbed71cfc17528de9f46e'),
    (3622, 'Vid/3622.vid', '084b90babc6fc18de397cd67c974bf980839c1caa33b6abe57c88d5e9e05cadd'),
    (3623, 'Vid/3623.vid', '107f53a22ab2e5e8d034cba976d82e32e6a3ff41a15cd761925053c00621bff2'),
    (3624, 'Vid/3624.vid', '3b901aeb5d2779bc7cf867f84f8646b14ee567426fd337151fe57b4562850fa4'),
    (3625, 'Vid/3625.vid', 'cc59d64360ce41e03d17714ef8bcfbba82e8a23bc2ed572f9364619a2b6a984e'),
    (3626, 'Vid/3626.vid', '6bd63752b4f5689306676dc3041919130d6f6eee2db19cc5d127643dae3958b6'),
    (3627, 'Vid/3627.vid', 'deead640412abde79c71f09c14d4fa983d9c57eea0ad4c39c8daa797f56b746f'),
    (3628, 'Vid/3628.vid', '25712587b0e9940f4b42985d4ebe073d91a636c6c27354e26eda9391e73cdbea'),
    (3745, 'Vid/1520.vid', '282925f762f5ee529f018500f2248683e709f3b5905a351a0f9dd53016c6b123'),
    (3750, 'Vid/3750.vid', '93d6d616895398d21382fd9e0752b6ee4267cf26d3fd38c14a5a772ea702c03a'),
    (3752, 'Vid/3752.vid', '72230662e6485240246e36b448c133dd00cd497f41b6f7424fee328488bd4aa0'),
    (1500, 'Vid/1500.vid', '45b034e0b548b6c0c7a752839c74ef4644304a3bb6e509263be47b0f8545503d'),
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_guarded(path: Path, expected: str) -> bytes:
    data = path.read_bytes()
    if sha256(data) != expected:
        raise ValueError(f'Unsupported source resource: {path}')
    return data


def _chunks(data: bytes, kind: bytes):
    if data[:4] != b'RES ' or data[8:12] != kind:
        raise ValueError(f'Expected RES/{kind!r}')
    if struct.unpack_from('<I', data, 4)[0] != len(data) - 8:
        raise ValueError('Invalid resource container length')
    pos = 12
    result = []
    while pos < len(data):
        if pos + 8 > len(data):
            raise ValueError('Truncated resource chunk')
        length = struct.unpack_from('<I', data, pos + 4)[0]
        end = pos + 8 + length
        if end > len(data):
            raise ValueError('Resource chunk exceeds file')
        result.append((data[pos:pos+4], data[pos+8:end]))
        pos = end
    return result


def _encode(kind: bytes, chunks) -> bytes:
    body = kind + b''.join(tag + struct.pack('<I', len(payload)) + payload
                           for tag, payload in chunks)
    return b'RES ' + struct.pack('<I', len(body)) + body


def _objects(data: bytes):
    chunks = _chunks(data, b'DATA')
    if [tag for tag, _ in chunks] != [b'OBJ ', b'WEAP', b'CNST', b'SFX ']:
        raise ValueError('Unsupported object database structure')
    rows = [row for _, row in records(chunks[0][1], 20)]
    index = {struct.unpack_from('<I', row)[0]: row for row in rows}
    if len(rows) != len(index):
        raise ValueError('Duplicate object definition')
    return chunks, rows, index


def _old_vid(data: bytes) -> tuple[bytes, dict]:
    """Remove only the new optional HEAD tail; preserve palette/frames.

    OLD reads the first ten header bytes at 0x425B1F..0x425C64, then the
    common loader reads cache metadata and locates PAL/CADR by chunk. Flag
    0x48 is also present in 31 stock OLD graphics, so no codec substitution
    is required. The additional 392 header bytes are Reloaded metadata.
    """
    chunks = _chunks(data, b'VID ')
    if [tag for tag, _ in chunks] != [b'HEAD', b'PAL ', b'CADR']:
        raise ValueError('Unsupported imported VID chunk layout')
    heads = list(records(chunks[0][1], 0))
    if len(heads) != 1 or len(heads[0][1]) not in (34, 426):
        raise ValueError('Unsupported imported VID header')
    header = heads[0][1]
    frames = list(records(chunks[2][1], 0))
    count = struct.unpack_from('<H', header, 4)[0]
    if len(frames) != count or not all(len(frame) >= 4 for _, frame in frames):
        raise ValueError('Imported VID frame count mismatch')
    converted = len(header) == 426
    if converted:
        chunks[0] = (b'HEAD', chunks[0][1][:12] + struct.pack('<I', 34) + header[:34])
    output = _encode(b'VID ', chunks)
    return output, {'header_bytes_before': len(header), 'header_bytes_after': 34,
                    'frame_count': count, 'palette_and_frames_unchanged': True}


def prepare(source: Path | None, old: Path) -> tuple[dict[str, bytes], dict]:
    """Prepare optional resources in memory from the user's two installations.

    None explicitly disables the import. A configured but unsupported source
    fails closed instead of silently dropping campaign maps.
    """
    if source is None:
        return {}, {'feature': FEATURE, 'enabled': False}
    source, old = Path(source), Path(old)
    old_data = _read_guarded(old / 'objects.res', OLD_OBJECTS_SHA256)
    new_data = _read_guarded(source / 'objects.res', RELOADED_OBJECTS_SHA256)
    chunks, rows, old_index = _objects(old_data)
    _, _, new_index = _objects(new_data)
    files, details, added = {}, [], []
    for source_vid, visual, digest in ASSETS:
        target_vid = ROAD_ALIAS[1] if source_vid == ROAD_ALIAS[0] else source_vid
        if target_vid in old_index:
            raise ValueError(f'Imported object would overwrite OLD VID {target_vid}')
        original = new_index[source_vid]
        name_end = original.index(b'\0', 4) + 1
        # Reviewed serialized OBJ body: 704 property bytes, then one visual
        # filename. Guarding the complete database prevents layout guessing.
        path_start = name_end + 704
        if original[path_start:].rstrip(b'\0').decode('ascii').replace('\\', '/').lower() != visual.lower():
            raise ValueError(f'Unexpected visual path for VID {source_vid}')
        output_name = f'Vid/coop_reloaded_{target_vid}.vid'
        row = struct.pack('<I', target_vid) + original[4:path_start]
        row += output_name.replace('/', '\\').encode('ascii') + b'\0'
        visual_bytes = _read_guarded(source / visual, digest)
        files[output_name], visual_details = _old_vid(visual_bytes)
        rows.append(row)
        added.append(target_vid)
        details.append({'source_vid': source_vid, 'target_vid': target_vid,
                        'source_file': visual, 'source_sha256': digest,
                        'file': output_name, 'sha256': sha256(files[output_name]),
                        **visual_details})
    payload = chunks[0][1][:8] + struct.pack('<I', len(rows))
    payload += b''.join(struct.pack('<I', len(row)) + row for row in rows)
    chunks[0] = (b'OBJ ', payload)
    files['objects.res'] = _encode(b'DATA', chunks)
    # No accidental changes to any OLD definition or non-OBJ chunk.
    result_chunks, _, result_index = _objects(files['objects.res'])
    if any(result_index[key] != value for key, value in old_index.items()):
        raise AssertionError('OLD object record changed')
    if result_chunks[1:] != _chunks(old_data, b'DATA')[1:]:
        raise AssertionError('OLD weapon/constant/sound data changed')

    maps = []
    for name, expected in MAPS:
        path = source / 'Maps' / name
        raw = _read_guarded(path, expected)
        parsed = parse_map(path, source / 'Maps/EXPORT.LGC')
        data = bytearray(raw)
        changes = []
        for sprite in parsed['sprites']:
            if sprite['vid'] == ROAD_ALIAS[0]:
                offset = int(sprite['sprite_offset'], 16) + 4
                struct.pack_into('<I', data, offset, ROAD_ALIAS[1])
                changes.append(offset)
        # Alias applies only to static map roads. Reject unexpected dynamic
        # VID references instead of allowing an incomplete object remapping.
        if any(c['opcode'] == 62 and c['args'][0] == ROAD_ALIAS[0]
               for sprite in parsed['sprites'] for stack in sprite['stacks'] for c in stack):
            raise ValueError('Unreviewed dynamic imported road VID reference')
        missing = sorted({s['vid'] for s in parsed['sprites']} - result_index.keys())
        if missing:
            raise ValueError(f'Missing imported map objects: {missing}')
        rel = f'Maps/{name}'
        files[rel] = bytes(data)
        maps.append({'file': rel, 'source_sha256': expected,
                     'sha256': sha256(data), 'road_alias_count': len(changes),
                     'road_alias_offsets': [hex(v) for v in changes]})
    metadata = {'feature': FEATURE, 'enabled': True, 'source': str(source.resolve()),
                'old_objects_sha256': OLD_OBJECTS_SHA256,
                'reloaded_objects_sha256': RELOADED_OBJECTS_SHA256,
                'objects_sha256': sha256(files['objects.res']),
                'added_objects': added, 'existing_objects_unchanged': True,
                'weapon_constant_sound_chunks_unchanged': True,
                'road_alias': {'from': ROAD_ALIAS[0], 'to': ROAD_ALIAS[1]},
                'graphics': details, 'maps': maps,
                'shared_asset_policy': 'Retain OLD shared graphics and object balance; import new dependencies and the eight-direction road only.',
                'native_visual_validation': 'Required; static format guards do not prove rendering or gameplay.'}
    return files, metadata


# Filled with the exact user-owned source maps, not generated runtime hashes.
MAPS = (
    ('Level_07_2.map', '39c5c2388db497d2a86ada94ffd505d24ff715306801c30143c939b680246d18'),
    ('Level_07_3.map', '0c7b10edb58b1730b9e05bd62fcdefb8afe15ce719e9f29d683841bbc0443608'),
)
