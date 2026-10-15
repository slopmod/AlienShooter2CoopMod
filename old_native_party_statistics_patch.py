"""Pure source-guarded mission-stat reset for the two native campaign heroes.

Original RememberStat resets skill35 on giCurArmy, which differs across peers.
Coop starts each mission by resetting that same mission accuracy denominator
for armies0 and3 in the same order. Single-player/survival behavior is retained.
No file or process writes, RNG calls, profile reset, or progression mutation.
"""
from __future__ import annotations

import hashlib

FEATURE = 'old-campaign-party-mission-statistics-v1'
SOURCE_SHA256 = '00041377816c259a249f5f60072f5ef40537a331834afce5a7b3907d610a03fb'
SOURCE_FILE = 'Maps/util_statistics.lgc'
ORIGINAL_RESET = '    SendCommandA(giCurArmy, EXT_SETSKILL, RPGHERO_MONSTERDAMAGE, 0 );  //zmTODO_ForNet\n'
PARTY_RESET = '''#ifdef COOP_CAMPAIGN
    SendCommandA(0, EXT_SETSKILL, RPGHERO_MONSTERDAMAGE, 0);
    SendCommandA(3, EXT_SETSKILL, RPGHERO_MONSTERDAMAGE, 0);
#else
''' + ORIGINAL_RESET + '''#endif
'''


def patch(source: bytes) -> tuple[str, dict]:
    if not isinstance(source, bytes):
        raise TypeError('Expected exact original util_statistics.lgc bytes')
    digest = hashlib.sha256(source).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError('Unsupported util_statistics.lgc source SHA-256')
    text = source.decode('cp1251').replace('\r\n', '\n')
    if text.count(ORIGINAL_RESET) != 1:
        raise ValueError('RememberStat local skill35 reset source guard failed')
    output = text.replace(ORIGINAL_RESET, PARTY_RESET)
    encoded = output.replace('\n', '\r\n').encode('cp1251')
    return output, {
        'feature': FEATURE, 'source_file': SOURCE_FILE,
        'input_sha256': digest, 'output_sha256': hashlib.sha256(encoded).hexdigest(),
        'scope': 'COOP_CAMPAIGN RememberStat mission-start reset only',
        'skill': 'RPGHERO_MONSTERDAMAGE', 'skill_id': 35,
        'army_order': [0, 3], 'value': 0,
        'vanilla_purpose': 'Reset current mission accuracy damage denominator',
        'original_noncoop_branch_preserved': True,
        'progression_or_inventory_setters_added': False,
        'rng_calls_added': 0,
        'runtime_tested': False,
    }
