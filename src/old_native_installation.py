"""Portable installation paths and cached production builds; no registry writes."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

from old_native_localization import get_language, tr
from old_native_paths import BUNDLE, MOD


CONFIG = MOD / 'campaign-installation.json'
OLD_SHA = '5128048a4ac922266f4664c1c00e18cc924b1fd3aafd451081799c8c519e3808'
VERSION = '0.5.0-preview'
PRODUCT = 'Alien Shooter 2 — Co-op Campaign'


def read_settings():
    try:
        value = json.loads(CONFIG.read_text('utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def source_root():
    configured = os.environ.get('AS2_COOP_GAME_DIR') or read_settings().get('source_game')
    if configured:
        return Path(configured).expanduser().resolve()
    candidates = (MOD.parent / 'Alien Shooter 2 old', MOD.parent.parent / 'Alien Shooter 2 old')
    return next((path for path in candidates if (path / 'AlienShooter.exe').is_file()), candidates[-1])


def validate_source(path):
    root = Path(path).expanduser().resolve()
    executable = root / 'AlienShooter.exe'
    if not executable.is_file():
        raise ValueError(tr('Выберите папку установленной старой Alien Shooter 2 с файлом AlienShooter.exe.',
                            'Select the original Alien Shooter 2 installation folder containing AlienShooter.exe.'))
    if hashlib.sha256(executable.read_bytes()).hexdigest() != OLD_SHA:
        raise ValueError(tr('Эта версия игры не поддерживается. Нужна проверенная русская старая Alien Shooter 2; '
                            'Reloaded и другие сборки EXE пока не подходят. Язык мода не меняет это требование.',
                            'Unsupported game version. The verified Russian original Alien Shooter 2 is required; '
                            'Reloaded and other EXE builds are not supported. The mod language does not change this requirement.'))
    required = ('AlienShooter.cfg', 'AlienShooter.exe.manifest', 'objects.res',
                'levels.cfg', 'campaign.cfg', 'input.cfg', 'Survive.cfg', 'Weapon.cfg',
                'Maps/EXPORT.LGC', 'Maps/COMMON.LGC', 'Maps/shop.map',
                'Text/Weapon.txt', 'Text/dialogs.txt') + tuple(
                    f'Maps/Level_{number:02d}.{extension}'
                    for number in range(1, 16) for extension in ('map', 'lgc'))
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise ValueError(tr('Установка игры неполная. Отсутствуют: ', 'Incomplete game installation. Missing: ') + ', '.join(missing))
    for name in ('Maps', 'Images', 'Vid', 'Text', 'Wav', 'Music', 'Speech'):
        if not (root / name).is_dir():
            raise ValueError(tr('Установка игры неполная: отсутствует папка ', 'Incomplete game installation. Missing folder: ') + name)
    return root


def save_reloaded_source(path):
    """Explicit developer/source override; normal releases use bundled maps.

    This runs before mission-dependent modules are imported by the worker.
    Validation imports only the resource reader, never the campaign registry.
    """
    value = 'disabled'
    if path is not None:
        from old_native_reloaded_assets import ASSETS, MAPS, RELOADED_OBJECTS_SHA256
        root = Path(path).expanduser().resolve()
        expected = {'objects.res': RELOADED_OBJECTS_SHA256}
        expected.update({f'Maps/{name}': digest for name, digest in MAPS})
        expected.update({name: digest for _, name, digest in ASSETS})
        for name, digest in expected.items():
            candidate = root / name
            if not candidate.is_file() or hashlib.sha256(candidate.read_bytes()).hexdigest() != digest:
                raise ValueError(tr('Неподдерживаемые или неполные ресурсы Reloaded: ', 'Unsupported or incomplete Reloaded resources: ') + name)
        for name in ('Maps/EXPORT.LGC', 'Maps/Level_07_2.lgc', 'Maps/Level_07_3.lgc',
                     'Maps/util_car.lgc', 'Maps/util_car2.lgc'):
            if not (root / name).is_file():
                raise ValueError(tr('Установка Reloaded неполная: отсутствует ', 'Incomplete Reloaded installation. Missing: ') + name)
        value = str(root)
    settings = read_settings()
    settings.update(schema=1, reloaded_game=value)
    temporary = CONFIG.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    temporary.replace(CONFIG)
    return None if value == 'disabled' else Path(value)


def save_source(path):
    root = validate_source(path)
    settings = read_settings()
    settings.update(schema=1, source_game=str(root), source_sha256=OLD_SHA)
    temporary = CONFIG.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    temporary.replace(CONFIG)
    return root


def build_fingerprint():
    """Changes to shipped builders/templates invalidate a cached runtime."""
    release = BUNDLE / 'campaign-release.json'
    digest = hashlib.sha256()
    digest.update(('mod-language:' + get_language()).encode('ascii'))
    from old_native_campaign_missions import RELOADED_ENABLED, RELOADED_ROOT
    digest.update(str(RELOADED_ENABLED).encode())
    if RELOADED_ENABLED:
        # Changing the optional source invalidates local cache, never peer IDs.
        digest.update(str(RELOADED_ROOT).encode('utf-8'))
    if getattr(sys, 'frozen', False):
        digest.update(json.loads(release.read_text('utf-8'))['build_fingerprint'].encode())
        return digest.hexdigest()
    paths = list(BUNDLE.glob('old_native_*.py')) + list((BUNDLE / 'templates').glob('*.lgc'))
    paths += [BUNDLE / name for name in ('launch_old_native_menu.py',)]
    paths += [BUNDLE / 'tools/map_format.py']
    paths += list((BUNDLE / 'locales').glob('*.json'))
    paths += list((BUNDLE / 'data').glob('*.json'))
    for path in sorted(paths):
        digest.update(path.relative_to(BUNDLE).as_posix().encode('utf-8'))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def cached_runtime(role, source, fingerprint):
    folder = MOD / 'runtime' / ('old-game-' + role)
    try:
        if not (folder / '.old-native-probe').is_file():
            return None
        stamp = json.loads((folder / 'campaign-installed.json').read_text('utf-8'))
        if stamp != {'schema': 1, 'source': str(source), 'build': fingerprint, 'role': role}:
            return None
        manifest = json.loads((folder / 'native-gameplay-build.json').read_text('utf-8'))
        if not manifest.get('startup_menu') or manifest.get('controls') or manifest.get('rng_trace'):
            return None
        for name, digest in manifest['files'].items():
            if hashlib.sha256((folder / name).read_bytes()).hexdigest() != digest:
                return None
        return folder
    except (OSError, KeyError, TypeError, ValueError):
        return None


def mark_installed(folder, role, source, fingerprint):
    (folder / 'campaign-installed.json').write_text(json.dumps({
        'schema': 1, 'source': str(source), 'build': fingerprint, 'role': role,
    }, indent=2) + '\n', 'utf-8')


def directplay_available():
    """Read-only prerequisite hint. Never installs Windows features or edits firewall."""
    if os.name != 'nt':
        return False
    windows = Path(os.environ.get('SystemRoot', r'C:\Windows'))
    return any((windows / name / 'dpnet.dll').is_file() for name in ('SysWOW64', 'System32'))
