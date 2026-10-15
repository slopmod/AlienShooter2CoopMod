"""Prepare verified game assets in a private campaign runtime directory."""
import hashlib
import json
import shutil
from old_native_installation import MOD, OLD_SHA, source_root

OLD = source_root()
ASSETS = ('cursores', 'Images', 'Maps', 'Music', 'Send', 'Speech', 'Text', 'Vid', 'Wav')


def prepare(role):
    prefix = 'old-game'
    if role not in ('host', 'client'):
        raise ValueError('Unknown campaign runtime role')
    original = (OLD / 'AlienShooter.exe').read_bytes()
    assert hashlib.sha256(original).hexdigest() == OLD_SHA, 'Unrecognized old EXE'
    target = MOD / 'runtime' / (prefix + '-' + role)
    target.mkdir(parents=True, exist_ok=True)
    # Retain the established marker so existing isolated runtimes stay repairable.
    marker = target / '.old-native-probe'
    if any(target.iterdir()) and not marker.is_file():
        raise RuntimeError('Refusing an unmarked runtime directory')
    marker.write_text(role, 'ascii')
    origin_path = target / '.original-game-source'
    origin = str(OLD.resolve())
    refresh_assets = origin_path.exists() and origin_path.read_text('utf-8') != origin
    for directory in ASSETS:
        for source in (OLD / directory).rglob('*'):
            if source.is_file():
                destination = target / source.relative_to(OLD)
                destination.parent.mkdir(parents=True, exist_ok=True)
                if refresh_assets or not destination.exists():
                    shutil.copy2(source, destination)
    origin_path.write_text(origin, 'utf-8')
    for filename in ('AlienShooter.exe.manifest', 'campaign.cfg', 'input.cfg',
                     'levels.cfg', 'Survive.cfg', 'Weapon.cfg', 'objects.res'):
        shutil.copy2(OLD / filename, target / filename)
    # Hash-guarded isolation patches keep saves local and both windows active. Neither
    # touches the networking paths. Both ranges contain no PE relocation fixups.
    patches = ((0x4181CD, '0f8c99010000', 'e99a01000090', 'Use CWD saves/logs'),
               (0x426F60, '0f8408020000', 'e93d02000090', 'Tick while hidden'))
    import pefile
    pe = pefile.PE(data=original)
    image_base = pe.OPTIONAL_HEADER.ImageBase
    patched = bytearray(original)
    for va, before, after, reason in patches:
        rva = va - image_base
        offset = pe.get_offset_from_rva(rva)
        before, after = bytes.fromhex(before), bytes.fromhex(after)
        assert patched[offset:offset + len(before)] == before, reason
        for block in getattr(pe, 'DIRECTORY_ENTRY_BASERELOC', []):
            for entry in block.entries:
                if entry.type:
                    assert not (entry.rva < rva + len(before) and entry.rva + 4 > rva), reason
        patched[offset:offset + len(before)] = after
    (target / 'AlienShooter.exe').write_bytes(patched)
    config = (OLD / 'AlienShooter.cfg').read_text('cp1251')
    title = 'Alien Shooter 2 - Coop Campaign' + (' - Player 2' if role == 'client' else '')
    config = config.replace('Title=AlienShooter2', 'Title=' + title)
    config = config.replace('RegPath=HKEY_CURRENT_USER\\SOFTWARE\\SigmaTeam\\AlienShooter2',
                            'RegPath=HKEY_CURRENT_USER\\SOFTWARE\\SigmaTeam\\AS2CoopPrototype\\' + prefix + '-' + role)
    config = config.replace('[game]', '[game]\nStartMap=maps\\mainmenu.map\nDebugMode=0\nUniqueLog=0')
    (target / 'AlienShooter.cfg').write_bytes(config.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp1251'))
    (target / 'runtime-isolation.json').write_text(json.dumps({'source_sha256': OLD_SHA,
        'patched_sha256': hashlib.sha256(patched).hexdigest(), 'role': role,
        'patches': patches, 'network_code_modified': False}, indent=2), 'utf-8')
    print('Prepared', target, flush=True)
    return target
