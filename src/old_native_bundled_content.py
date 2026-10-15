"""Pinned content subset needed to import the two additional road missions.

This is not a second game installation. Only the explicit, already reviewed
map/script/graphics dependencies enter the release; the OLD engine and its
ordinary campaign resources still come from the player's installed game.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil


FEATURE = 'old-reloaded-bundled-content-v1'
RELATIVE_ROOT = Path('campaign-content/reloaded')
MANIFEST_NAME = 'bundle-manifest.json'


def file_hashes() -> dict[str, str]:
    """The complete allowlist, sharing existing importer's visual/map guards."""
    from old_native_reloaded_assets import ASSETS, MAPS, RELOADED_OBJECTS_SHA256
    from old_native_reloaded_scripts import RELOADED_CAR_SHA256, RELOADED_CAR2_SHA256
    from old_native_reloaded_endwave import SOURCE, SOURCE_SHA256
    files = {
        'objects.res': RELOADED_OBJECTS_SHA256,
        'Maps/EXPORT.LGC': 'c204f5991f16e1b0547824b5183447dec66fa61509a2fef92a908f3bbe00e706',
        'Maps/Level_07_2.lgc': 'c4844084b419a49def7e826ba4dbcab2916ead2ce1a4dda6389da6f55f62f635',
        'Maps/Level_07_3.lgc': 'c4844084b419a49def7e826ba4dbcab2916ead2ce1a4dda6389da6f55f62f635',
        'Maps/util_car.lgc': RELOADED_CAR_SHA256,
        'Maps/util_car2.lgc': RELOADED_CAR2_SHA256,
        SOURCE: SOURCE_SHA256,
    }
    files.update(('Maps/' + name, digest) for name, digest in MAPS)
    files.update((name, digest) for _, name, digest in ASSETS)
    return dict(sorted(files.items()))


def _file(root: Path, relative: str) -> Path:
    candidate = root / relative
    # All names originate in the code allowlist, never in an untrusted manifest.
    if root not in candidate.resolve().parents:
        raise ValueError('Bundled content path escapes its directory: ' + relative)
    for path in (candidate, *candidate.parents):
        if path == root:
            break
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise ValueError('Bundled content must not contain filesystem links: ' + relative)
    if not candidate.is_file():
        raise ValueError('Bundled content is incomplete: ' + relative)
    return candidate


def _sha(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _inventory(root: Path) -> dict[str, dict]:
    files = {}
    for name, expected in file_hashes().items():
        path = _file(root, name)
        digest = _sha(path)
        if digest != expected:
            raise ValueError('Unsupported or damaged bundled content: ' + name)
        files[name] = {'sha256': digest, 'size': path.stat().st_size}
    return files


def verify_bundle(folder: Path) -> dict:
    """Verify every file against code pins, and reject unlisted payloads."""
    folder = Path(folder).resolve()
    manifest_path = _file(folder, MANIFEST_NAME)
    try:
        manifest = json.loads(manifest_path.read_text('utf-8'))
    except (OSError, ValueError) as error:
        raise ValueError('The additional mission content manifest is damaged') from error
    if not isinstance(manifest, dict) or manifest.get('schema') != 1 or manifest.get('feature') != FEATURE:
        raise ValueError('Unsupported additional mission content manifest')
    files = _inventory(folder)
    expected = {
        'schema': 1, 'feature': FEATURE, 'missions': [72, 73],
        'files': files, 'total_bytes': sum(item['size'] for item in files.values()),
    }
    if manifest != expected:
        raise ValueError('Additional mission content manifest does not match its files')
    allowed = {Path(name) for name in files} | {Path(MANIFEST_NAME)}
    allowed |= {parent for name in files for parent in Path(name).parents if parent != Path('.')}
    for candidate in folder.rglob('*'):
        if (candidate.is_symlink()
                or (hasattr(candidate, 'is_junction') and candidate.is_junction())
                or candidate.relative_to(folder) not in allowed):
            raise ValueError('Unlisted file in additional mission content: ' + candidate.name)
    return manifest


def prepare_bundle(source: Path, destination: Path) -> dict:
    """Copy the reviewed subset into a new/empty release content directory.

    The complete source is checked before creating output. No recursive source
    copying, generated runtime files, executable, or personal data is included.
    Existing nonempty destinations are refused rather than replaced.
    """
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or destination in source.parents:
        raise ValueError('The bundle destination must be separate from its source')
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError('The bundle destination must be new or empty')
    files = _inventory(source)
    manifest = {
        'schema': 1, 'feature': FEATURE, 'missions': [72, 73],
        'files': files, 'total_bytes': sum(item['size'] for item in files.values()),
    }
    destination.mkdir(parents=True, exist_ok=True)
    for name in files:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_file(source, name), target)
    (destination / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    return verify_bundle(destination)


def bundled_root(bundle: Path | None = None) -> Path | None:
    """Locate the shipped subset; a damaged installed bundle must fail closed."""
    if bundle is None:
        from old_native_installation import BUNDLE
        bundle = BUNDLE
    folder = Path(bundle) / RELATIVE_ROOT
    if not folder.exists():
        return None
    try:
        verify_bundle(folder)
    except (OSError, ValueError) as error:
        raise ValueError('Повреждены файлы дополнительных миссий. Переустановите мод. '
                         + str(error)) from error
    return folder.resolve()
