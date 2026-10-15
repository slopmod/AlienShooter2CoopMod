"""Apply reviewed, language-independent deadlines to original dialogue slots.

The canonical table was derived once from the supported Russian OLD assets.
Never derive simulation timing from the local voice pack: translated or absent
audio must not change when the campaign advances. Original text and speech paths
are preserved; dialogue IDs, speech order and pause controls must still match.
"""
import hashlib
import json
import re
import struct
from pathlib import Path, PureWindowsPath

SPEECH = re.compile(r'^(\s*<Speech=([^>\r\n]+)>)[ \t]*$', re.MULTILINE)
MANIFEST = Path(__file__).resolve().parent / 'data' / 'old-russian-dialogue-timing.json'
CANONICAL_SHA256 = 'de89687f807fbb6d3d3dbebf3c35b2a3d08e6593fae140aee5d22db18234dfb2'
FEATURE = 'old-campaign-speech-deadlines-v2'
PRESENTATION = re.compile(r'<(?:Font|DefaultFontForRadio|Coor|Icon|SFX)=[^>\r\n]+>')


def _asset_name(name: str) -> str:
    relative = PureWindowsPath(name)
    if (relative.is_absolute() or relative.drive or '..' in relative.parts
            or not relative.parts or relative.parts[0].lower() != 'speech'
            or relative.suffix.lower() != '.ogg'):
        raise ValueError('Unexpected speech asset path')
    return str(relative).lower()


def _topology(text: str) -> list[str]:
    """Keep every dialogue/control slot, including unvoiced dialogue contexts.

    Font, portrait, sound effect and coordinate tags are presentation settings;
    they do not select the simulation deadline. Unknown controls require review
    rather than being treated as translated prose.
    """
    result = []
    for line in text.splitlines():
        token = line.strip()
        if not token.startswith('<'):
            continue
        if re.fullmatch(r'<\d+(?:_\d+)?>', token) or token == '<pause>':
            result.append(token)
        elif match := re.fullmatch(r'<Speech=([^>\r\n]+)>', token):
            result.append('<Speech=' + _asset_name(match.group(1)) + '>')
        elif not PRESENTATION.fullmatch(token):
            raise ValueError('Unsupported dialogue control requires timing review: ' + token)
    return result


def _canonical() -> dict:
    raw = MANIFEST.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CANONICAL_SHA256:
        raise ValueError('Canonical dialogue timing manifest is missing or modified')
    value = json.loads(raw)
    if value.get('schema') != 1 or value.get('feature') != FEATURE:
        raise ValueError('Unsupported canonical dialogue timing manifest')
    return value


def vorbis_duration_ms(data: bytes) -> int:
    offset, rate, serial, last, ended = 0, None, None, None, False
    while offset < len(data):
        if ended or offset + 27 > len(data) or data[offset:offset + 5] != b'OggS\0':
            raise ValueError('Unsupported or truncated Ogg stream')
        flags = data[offset + 5]
        granule = struct.unpack_from('<Q', data, offset + 6)[0]
        page_serial = struct.unpack_from('<I', data, offset + 14)[0]
        segments = data[offset + 26]
        start = offset + 27 + segments
        if start > len(data):
            raise ValueError('Truncated Ogg lacing table')
        end = start + sum(data[offset + 27:start])
        if end > len(data):
            raise ValueError('Truncated Ogg page')
        if rate is None:
            body = data[start:end]
            if not flags & 2 or len(body) < 30 or body[:7] != b'\x01vorbis':
                raise ValueError('Expected Vorbis identification page')
            rate = struct.unpack_from('<I', body, 12)[0]
            if not 8000 <= rate <= 192000:
                raise ValueError('Unsupported Vorbis sample rate')
            serial = page_serial
        if serial != page_serial:
            raise ValueError('Chained/multiplexed Ogg streams are unsupported')
        if granule != 0xFFFFFFFFFFFFFFFF:
            if last is not None and granule < last:
                raise ValueError('Ogg granule position moved backwards')
            last = granule
        ended = bool(flags & 4)
        offset = end
    if not ended or rate is None or not last:
        raise ValueError('Missing complete Vorbis end position')
    result = (last * 1000 + rate - 1) // rate
    if not 1 <= result <= 600000:
        raise ValueError('Unexpected speech duration')
    return result


def prepare(old_root: Path) -> tuple[str, dict]:
    root = Path(old_root).resolve()
    original = (root / 'Text' / 'dialogs.txt').read_bytes()
    text = original.decode('cp1251').replace('\r\n', '\n')
    canonical = _canonical()
    topology = _topology(text)
    if topology != canonical['topology']:
        mismatch = next((index for index, (a, b) in enumerate(zip(topology, canonical['topology']))
                         if a != b), min(len(topology), len(canonical['topology'])))
        raise ValueError('Dialogue IDs, speech slots or pause order differ from canonical timings '
                         f'at control slot {mismatch}; a reviewed timing mapping is required')
    clips = canonical['clips']

    def replace(match):
        deadline = clips[_asset_name(match.group(2))]['deadline_ms']
        return match.group(1) + '\n<PauseDuration=' + str(deadline) + '>'

    result, count = SPEECH.subn(replace, text)
    if count != canonical['phrases']:
        raise ValueError('Canonical dialogue speech count mismatch')
    return result, {'feature': FEATURE,
                    'source_sha256': hashlib.sha256(original).hexdigest(),
                    'canonical_sha256': CANONICAL_SHA256,
                    'reference_dialogues_sha256': canonical['reference']['dialogues_sha256'],
                    'phrases': count, 'unique_assets': len(clips),
                    'margin_ms': canonical['margin_ms'],
                    'dialogue_duration_scale': canonical['dialogue_duration_scale'],
                    'local_audio_controls_timing': False,
                    'clips': clips}
