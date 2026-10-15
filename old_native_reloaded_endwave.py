"""Restore Reloaded 7.3's native named-generator completion handshake in OLD.

The imported physical map keeps OLD's logical campaign index 7. Reloaded's
common script instead selected this callback using its own index 9, so that
callback must travel with the physical map rather than either index table.
"""
import hashlib
from pathlib import Path
import struct


SOURCE = 'Maps/common_compaign.lgc'
SOURCE_SHA256 = '85b50abbc495a1c084d130e974fa045e989530b3069e7c689663e3ad29a577f8'
MAP = 'Maps/Level_07_3.map'
MAP_SHA256 = '0c7b10edb58b1730b9e05bd62fcdefb8afe15ce719e9f29d683841bbc0443608'
# Reverse-stored native exit: approach -> Action10=1 -> await Action10=2
# -> smaller approach -> Action9=1. No new exit or quest setter is introduced.
EXIT_COMMANDS = (
    (0xE57FB, (43, 16557, 1502, 750)),
    (0xE57EB, (131, 10, 1, 0)),
    (0xE57DB, (79, 10, 2, 0)),
    (0xE57CB, (43, 16557, 1502, 180)),
    (0xE57BB, (131, 9, 1, 0)),
)
NATIVE_PREDICATE = '''int num = SendCommand(EXT_GetNamedMonst, 1);
    \tiff(num == 0 && !Z_DEBUG2)
    \t{
    \t\tAction10 = 2;'''

HELPER = r'''
// Reloaded common_compaign.lgc:253-259. This is normal campaign logic,
// including its original native named-m1 counter and one-shot iff latch.
OldLevel73EndWaveTact()
{
    if(ToLower(GetMapName()) != "maps\\level_07_3.map") return;
    int num = SendCommand(EXT_GetNamedMonst, 1);
    iff(num == 0)
    {
        Action10 = 2;
        Log2("OldLevel73: original named m1 generators destroyed");
    }
}

'''


def validate_sources(root):
    root = Path(root)
    source = (root / SOURCE).read_bytes()
    data = (root / MAP).read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unsupported Reloaded end-wave source')
    if hashlib.sha256(data).hexdigest() != MAP_SHA256:
        raise ValueError('Unsupported Reloaded end-wave map')
    text = source.decode('cp1251').replace('\r\n', '\n')
    if text.count(NATIVE_PREDICATE) != 1:
        raise ValueError('Reloaded native named-group predicate changed')
    for offset, command in EXIT_COMMANDS:
        if struct.unpack_from('<4i', data, offset) != command:
            raise ValueError('Reloaded end-wave exit stack changed')


def adapt_entry(source, reloaded_root=None):
    from old_native_campaign_progression import once
    if 'OldLevel73EndWaveTact' in source:
        raise ValueError('Reloaded end-wave adapter already applied')
    if reloaded_root is None:
        from old_native_campaign_missions import RELOADED_ROOT
        reloaded_root = RELOADED_ROOT
    if reloaded_root is None:
        raise ValueError('Reloaded source required for Level 7.3')
    validate_sources(reloaded_root)
    source = once(source, 'main()\n{', HELPER + 'main()\n{')
    return once(source, '  CompaignGameTact();',
                '  CompaignGameTact();\n  OldLevel73EndWaveTact();')
