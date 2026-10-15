"""Build the standalone Windows launcher, portable ZIP and per-user installer.

Run with 64-bit Python 3.11+ after installing requirements.txt into
tools/vendor and requirements-build.txt into tools/packaging. Does not launch the game.
Includes only the pinned additional-mission content subset. The base OLD game
still comes from the player's installation. Previous releases are retained.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import zipfile

SOURCE = Path(__file__).resolve().parent.parent / 'src'
sys.path.insert(0, str(SOURCE))

from old_native_installation import MOD, OLD_SHA, PRODUCT, VERSION, build_fingerprint


NAME = 'AS2CoopCampaign'
VENDOR = MOD / 'tools/vendor'
PACKAGING = MOD / 'tools/packaging'
TEMPLATES = (
    'old_campaign_init.lgc', 'old_campaign_transition.lgc',
    'old_game_lobby.lgc', 'old_game_observe.lgc',
)


def inside(path: Path, root: Path) -> Path:
    """Resolve before every directory promotion/archive; reject escaped paths."""
    path, root = path.resolve(), root.resolve()
    if path == root or root not in path.parents:
        raise ValueError('Build output must remain inside its designated directory')
    return path


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def json_file(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', 'utf-8')


def package_info(name: str, search: Path):
    normalized = name.lower().replace('_', '-')
    for distribution in metadata.distributions(path=[str(search)]):
        actual = distribution.metadata.get('Name', '').lower().replace('_', '-')
        if actual == normalized:
            return distribution
    raise RuntimeError(f'{name} is not installed in {search}')


def source_revision() -> dict:
    """Record the source checkout when Git is available, including dirty state."""
    try:
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=MOD,
                                check=True, capture_output=True, text=True).stdout.strip()
        status = subprocess.run(['git', 'status', '--porcelain'], cwd=MOD,
                                check=True, capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return {'commit': None, 'dirty': None}
    return {'commit': commit, 'dirty': bool(status.strip())}


def collect_licenses(destination: Path, compiler: Path) -> dict:
    """Copy real license files; never synthesize replacement license terms."""
    destination.mkdir()
    versions = {}
    index = ['Third-party notices accompanying AS2CoopCampaign', '',
             'License files below are copied verbatim from the build dependencies.',
             'The base Alien Shooter 2 game is not included. Two additional',
             'campaign maps and their required resources accompany this mod.', '']
    for name, source in (('capstone', VENDOR), ('pefile', VENDOR), ('pyinstaller', PACKAGING)):
        distribution = package_info(name, source)
        versions[name] = distribution.version
        files = []
        for entry in distribution.files or ():
            if not any(word in entry.name.lower() for word in ('license', 'copying', 'copyright')):
                continue
            original = Path(distribution.locate_file(entry))
            if original.is_file():
                files.append((entry, original))
        if not files:
            raise RuntimeError(f'Installed {name} metadata contains no readable license files')
        folder = destination / name
        folder.mkdir()
        for number, (entry, original) in enumerate(files, 1):
            target = folder / f'{number:02d}-{entry.name}'
            shutil.copyfile(original, target)
            index.append(f'{name} {distribution.version}: {target.relative_to(destination).as_posix()}')
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if not python_license.is_file():
        raise RuntimeError('The Python installation has no LICENSE.txt to redistribute')
    shutil.copyfile(python_license, destination / 'Python-LICENSE.txt')
    versions['python'] = sys.version.split()[0]
    index.append(f'Python {versions["python"]}: Python-LICENSE.txt')
    # The official Windows Python installer carries the combined runtime
    # notices in LICENSE.txt and Tk's license in its Tcl library directory.
    tk_licenses = sorted((Path(sys.base_prefix) / 'tcl').glob('tk*/license.terms'))
    if not tk_licenses:
        raise RuntimeError('The Tk installation has no license.terms to redistribute')
    for original in tk_licenses:
        target = destination / f'{original.parent.name}-license.terms'
        shutil.copyfile(original, target)
        index.append(f'{original.parent.name}: {target.name}')
    shutil.copyfile(compiler.parent / 'license.txt', destination / 'InnoSetup-LICENSE.txt')
    index.append('Installer built with Inno Setup: https://jrsoftware.org/')
    (destination / 'README.txt').write_text('\n'.join(index) + '\n', 'utf-8')
    return versions


def version_resource(path: Path) -> None:
    numbers = tuple(int(part) for part in VERSION.split('-')[0].split('.'))
    if len(numbers) != 3:
        raise ValueError('Expected a three-part product version')
    version = (*numbers, 0)
    strings = {
        'FileDescription': PRODUCT,
        'FileVersion': VERSION,
        'ProductName': PRODUCT,
        'ProductVersion': VERSION,
        'OriginalFilename': NAME + '.exe',
    }
    entries = ',\n'.join(f'StringStruct({key!r}, {value!r})' for key, value in strings.items())
    russian = dict(strings, FileDescription='Alien Shooter 2 — Совместная кампания',
                   ProductName='Alien Shooter 2 — Совместная кампания')
    russian_entries = ',\n'.join(f'StringStruct({key!r}, {value!r})' for key, value in russian.items())
    path.write_text(
        f'VSVersionInfo(ffi=FixedFileInfo(filevers={version!r}, prodvers={version!r},\n'
        'mask=0x3f, flags=0x2, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),\n'
        'kids=[StringFileInfo([StringTable("040904b0", [\n' + entries + '\n]),\n'
        'StringTable("041904b0", [\n' + russian_entries + '\n])]),\n'
        'VarFileInfo([VarStruct("Translation", [1033, 1200, 1049, 1200])])])\n', 'utf-8')


def audit_release(folder: Path) -> list[Path]:
    """Only packaging outputs/templates/docs may enter a transferable archive."""
    required = (
        NAME + '.exe', 'INSTALL_RU.txt', 'INSTALL_EN.txt', 'campaign-release.json',
        '_internal/campaign-release.json', '_internal/capstone/lib/capstone.dll',
        'LICENSES/README.txt', '_internal/campaign-content/reloaded/bundle-manifest.json',
        '_internal/data/old-russian-dialogue-timing.json', '_internal/locales/native-ui.json',
    )
    for relative in required:
        if not (folder / relative).is_file():
            raise RuntimeError('Missing release file: ' + relative)
    files = []
    forbidden_parts = {'runtime', 'reports', 'saves', 'logs', '.git', '.codex', '.agents'}
    forbidden_names = {'alienshooter.exe', 'objects.res', 'campaign-installation.json',
                       'campaign-language.txt',
                       'native-campaign-menu-status.json', 'native-gameplay-build.json'}
    from old_native_bundled_content import RELATIVE_ROOT, MANIFEST_NAME, verify_bundle
    content_prefix = Path('_internal') / RELATIVE_ROOT
    content = verify_bundle(folder / content_prefix)
    content_files = {content_prefix / name for name in content['files']}
    content_files.add(content_prefix / MANIFEST_NAME)
    for candidate in sorted(folder.rglob('*')):
        # No symlink/junction target is allowed to pull unrelated content in.
        inside(candidate, folder)
        if candidate.is_symlink() or (hasattr(candidate, 'is_junction') and candidate.is_junction()):
            raise RuntimeError('Release includes an unexpected filesystem link')
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(folder)
        if relative not in content_files and (forbidden_parts.intersection(part.lower() for part in relative.parts)
                or candidate.name.lower() in forbidden_names
                or candidate.suffix.lower() in {'.map', '.men', '.sav', '.log'}):
            raise RuntimeError('Unexpected game/private file in release: ' + relative.as_posix())
        if 'research' in relative.parts:
            raise RuntimeError('Unexpected research data in release: ' + relative.as_posix())
        if 'templates' in relative.parts:
            expected = Path('_internal/templates') / candidate.name
            if relative != expected or candidate.name not in TEMPLATES:
                raise RuntimeError('Unexpected template in release: ' + relative.as_posix())
        files.append(candidate)
    return files


def main() -> int:
    global VENDOR, PACKAGING
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path, default=MOD / 'tools/packaging-inno/compiler/ISCC.exe')
    parser.add_argument('--vendor', type=Path, default=VENDOR,
                        help='Directory populated with requirements.txt')
    parser.add_argument('--packaging', type=Path, default=PACKAGING,
                        help='Directory populated with requirements-build.txt')
    parser.add_argument('--reloaded-source', type=Path, required=True,
                        help='Build-time source for the two included additional maps')
    args = parser.parse_args()
    VENDOR, PACKAGING = args.vendor.resolve(), args.packaging.resolve()
    sys.path.insert(0, str(VENDOR))
    # A release build must not inherit a developer's local language/content
    # settings. Both language catalogs are shipped; the installer sets preference.
    os.environ['AS2_COOP_LANGUAGE'] = 'en'
    os.environ['AS2_COOP_RELOADED_DIR'] = str(args.reloaded_source.resolve())
    compiler = args.compiler.resolve()
    if not compiler.is_file():
        raise RuntimeError('Install Inno Setup and pass --compiler <path to ISCC.exe>')
    if os.name != 'nt' or struct.calcsize('P') != 8 or sys.version_info < (3, 11):
        raise RuntimeError('Build with 64-bit Windows Python 3.11 or later')
    if getattr(sys, 'frozen', False):
        raise RuntimeError('The release builder must run from the source checkout')
    # All mutable destinations are local, explicit, and checked before use.
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    build_root = inside(MOD / 'build/campaign-release' / stamp, MOD)
    dist_root = inside(MOD / 'dist', MOD)
    build_root.mkdir(parents=True)
    dist_root.mkdir(exist_ok=True)
    resources = build_root / 'resources'
    resources.mkdir()
    license_dir = resources / 'LICENSES'
    dependencies = collect_licenses(license_dir, compiler)
    from old_native_bundled_content import RELATIVE_ROOT, prepare_bundle
    content_folder = resources / RELATIVE_ROOT
    content = prepare_bundle(args.reloaded_source, content_folder)
    fingerprint = build_fingerprint()
    manifest = {
        'schema': 1, 'product': PRODUCT, 'version': VERSION, 'platform': 'windows-x64',
        'build_fingerprint': fingerprint, 'supported_game_exe_sha256': OLD_SHA,
        'python_required_on_player_pc': False, 'game_files_included': True,
        'base_game_included': False, 'reloaded_installation_required': False,
        'included_content': content,
        'supported_game': 'Russian original Alien Shooter 2 1.1 (v1.1-rus), verified Gold installation',
        'supported_game_file_version': '2.5.0.1', 'supported_game_exe_size': 2244608,
        'default_language': 'en', 'supported_languages': ['en', 'ru'],
        'same_language_required': True, 'original_game_language': 'ru',
        'english_game_executable_supported': False,
        'dialogue_timing_basis': 'canonical-russian-original',
        'dependencies': dependencies, 'source': source_revision(),
        'templates': {name: sha(SOURCE / 'templates' / name) for name in TEMPLATES},
    }
    manifest_file = resources / 'campaign-release.json'
    json_file(manifest_file, manifest)
    version_file = resources / 'version-info.txt'
    version_resource(version_file)
    environment = os.environ.copy()
    environment['PYTHONPATH'] = os.pathsep.join((str(PACKAGING), str(VENDOR), str(SOURCE)))
    environment['PYTHONHASHSEED'] = '0'
    arguments = [
        sys.executable, '-B', '-m', 'PyInstaller', '--onedir', '--windowed',
        '--name', NAME, '--noupx', '--contents-directory', '_internal',
        '--distpath', str(build_root / 'dist'), '--workpath', str(build_root / 'work'),
        '--specpath', str(build_root), '--paths', str(VENDOR), '--paths', str(SOURCE),
        '--version-file', str(version_file), '--hidden-import', 'pefile',
        '--hidden-import', 'capstone', '--collect-submodules', 'ordlookup',
        '--collect-submodules', 'capstone',
        '--add-binary', str(VENDOR / 'capstone/lib/capstone.dll') + ';capstone/lib',
        '--add-data', str(manifest_file) + ';.',
        '--add-data', str(content_folder) + ';' + RELATIVE_ROOT.as_posix(),
        '--add-data', str(SOURCE / 'data/old-russian-dialogue-timing.json') + ';data',
        '--add-data', str(SOURCE / 'locales/native-ui.json') + ';locales',
    ]
    for name in TEMPLATES:
        arguments += ['--add-data', str(SOURCE / 'templates' / name) + ';templates']
    arguments.append(str(SOURCE / 'campaign_launcher.py'))
    print('Building the standalone launcher; the game will not be started.', flush=True)
    subprocess.run(arguments, cwd=MOD, env=environment, check=True)
    staged = inside(build_root / 'dist' / NAME, build_root)
    for guide in ('INSTALL_EN.txt', 'INSTALL_RU.txt'):
        shutil.copyfile(MOD / guide, staged / guide)
    shutil.copyfile(manifest_file, staged / 'campaign-release.json')
    shutil.copytree(license_dir, staged / 'LICENSES')
    audit_release(staged)
    final = inside(dist_root / NAME, dist_root)
    if final.exists():
        previous = inside(dist_root / (NAME + '-previous-' + stamp), dist_root)
        final.rename(previous)
        print('Previous release retained:', previous.relative_to(MOD), flush=True)
    staged.rename(final)
    files = audit_release(final)
    inventory = {path.relative_to(final).as_posix(): sha(path) for path in files}
    json_file(final / 'release-files.json', {'schema': 1, 'sha256': inventory})
    # Archive only this freshly audited release; never the checkout or runtime.
    archive = inside(dist_root / f'{NAME}-{VERSION}-windows-x64.zip', dist_root)
    temporary = inside(archive.with_suffix('.zip.tmp'), dist_root)
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in audit_release(final):
            output.write(path, Path(NAME) / path.relative_to(final))
    temporary.replace(archive)
    archive.with_suffix('.zip.sha256').write_text(sha(archive) + '  ' + archive.name + '\n', 'ascii')
    # Compile exactly the audited portable release. User-generated files never
    # enter this directory, and Inno does not remove them during uninstall.
    subprocess.run([str(compiler), '/Qp', '/DReleaseDir=' + str(final),
                    '/DOutputDir=' + str(dist_root), '/DAppVersion=' + VERSION,
                    str(MOD / 'scripts/campaign-installer.iss')], check=True, cwd=MOD)
    installer = dist_root / f'{NAME}-{VERSION}-setup.exe'
    if not installer.is_file():
        raise RuntimeError('Compiler did not produce the expected installer')
    installer.with_suffix('.exe.sha256').write_text(sha(installer) + '  ' + installer.name + '\n', 'ascii')
    print('Ready:', final.relative_to(MOD) / (NAME + '.exe'), flush=True)
    print('Archive:', archive.relative_to(MOD), flush=True)
    print('Installer:', installer.relative_to(MOD), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
