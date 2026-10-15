"""Bind compiled campaign triggers and hero dialogue to story hero 0.

Pure byte transformation for the exact supplied OLD executable. The caller
must apply it only to isolated campaign copies, before the optional input
fixture. This does not change local player identity or network transport.
"""
import hashlib

BASELINE_SHA256 = '5128048a4ac922266f4664c1c00e18cc924b1fd3aafd451081799c8c519e3808'
IMAGE_BASE = 0x400000
STORY_PATCHES = (
    (0x44D297, bytes.fromhex('8b91bc090000'), bytes.fromhex('ba0000000090')),
    (0x44D2BD, bytes.fromhex('8b81bc090000'), bytes.fromhex('b80000000090')),
    (0x44E4E8, bytes.fromhex('8b91bc090000'), bytes.fromhex('ba0000000090')),
    (0x44E502, bytes.fromhex('8b81bc090000'), bytes.fromhex('b80000000090')),
    # Deadline is in simulation milliseconds, independent of UI speed settings.
    (0x4ADD43, bytes.fromhex('8b4a54'), bytes.fromhex('6a6459')),
    # Once that deadline passes, do not wait on local audio playback status.
    (0x4AE9DB, bytes.fromhex('8b11ff5204'), bytes.fromhex('e918000000')),
    # Prototype dialogues advance automatically; raw local skip is not shared.
    (0x4AE99C, bytes.fromhex('85c0'), bytes.fromhex('31c0')),
)
ISOLATION_PATCHES = (
    (0x4181CD, bytes.fromhex('0f8c99010000'), bytes.fromhex('e99a01000090')),
    (0x426F60, bytes.fromhex('0f8408020000'), bytes.fromhex('e93d02000090')),
)


def patch(image: bytes) -> tuple[bytes, dict]:
    if not isinstance(image, bytes):
        raise TypeError('Expected executable bytes')
    normalized = bytearray(image)
    for va, before, after in ISOLATION_PATCHES + STORY_PATCHES:
        offset = va - IMAGE_BASE  # Verified .text RVA == raw offset in this PE.
        current = image[offset:offset + len(before)]
        if current not in (before, after):
            raise ValueError(f'Unknown executable bytes at {va:#x}')
        normalized[offset:offset + len(before)] = before
    if hashlib.sha256(normalized).hexdigest() != BASELINE_SHA256:
        raise ValueError('Unsupported campaign executable: normalized SHA-256 mismatch')
    output = bytearray(image)
    for va, before, after in STORY_PATCHES:
        output[va - IMAGE_BASE:va - IMAGE_BASE + len(before)] = after
    output = bytes(output)
    return output, {
        'feature': 'old-campaign-story-dialogue-v3',
        'baseline_sha256': BASELINE_SHA256,
        'input_sha256': hashlib.sha256(image).hexdigest(),
        'output_sha256': hashlib.sha256(output).hexdigest(),
        'scope': 'Canonical story hero and simulation-time dialogue; isolated campaign only',
        'requires_dialogue_deadline_assets': True,
        'manual_dialogue_skip': False,
        'story_army': 0,
        'patches': [{'va': hex(va), 'before': before.hex(), 'after': after.hex()}
                    for va, before, after in STORY_PATCHES],
    }
