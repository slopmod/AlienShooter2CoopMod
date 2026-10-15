"""Compose shared campaign events once, with each stage's hash kept explicit."""
import hashlib
from pathlib import Path


def _digest(source):
    return hashlib.sha256(source.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp1251')).hexdigest()


def prepare(root, *, shared_money, progression):
    from old_native_dynamite_patch import patch as patch_dynamite
    from old_native_shared_money_scripts import patch_campaign
    from old_native_campaign_progression import once

    source, dynamite = patch_dynamite((Path(root) / 'Maps/common_compaign.lgc').read_bytes())
    for before, after in (
        ('SendCommandA( -1, EXT_ADDITEMBYBASEID, Action4 );',
         'SendCommandA( 0, EXT_ADDITEMBYBASEID, Action4 );'),
        ('SpotLightOff(giCurArmy);', 'SpotLightOff(0);'),
    ):
        source = once(source, before, after)
    money = None
    if shared_money:
        source, money = patch_campaign(source)
    extensions = None
    if progression:
        from old_native_level10_specials import adapt_common
        from old_native_demolition_sources import adapt_common as adapt_demolition
        before = _digest(source)
        source = adapt_common(source)
        source = adapt_demolition(source, root)
        extensions = dict(feature='old-campaign-common-events-v2', input_sha256=before,
                          output_sha256=_digest(source), per_terminal_downloads=True,
                          admitted_demolition_sources=True)
    dynamite['output_sha256'] = _digest(source)
    return source, dynamite, money, extensions
