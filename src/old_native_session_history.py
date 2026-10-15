"""Keep a small before/after evidence bundle for each manual native session.

Call capture while holding old_native_session_lock: before builders/configuration
can replace bridge files, and after all owned game processes have closed.
Only the explicitly named current logs and checkpoint evidence are copied.
Archiving failures are diagnostic and must not prevent playing the game.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import uuid


EVIDENCE_FILES = (
    'Logs/error.log',
    'Logs/error_fatal.log',
    'coop-save.pending.txt',
    'coop-save-status.txt',
    'coop-out-0.txt',
    'coop-out-3.txt',
    'coop-out-quests.txt',
    'coop-menu-catalog.txt',
    'coop-menu-status.txt',
    'coop-resume-mode.txt',
    'old-campaign-init-state.txt',
    'old-game-lobby-state.txt',
    'old-network-command-state.txt',
    'native-gameplay-build.json',
)


class NativeSessionHistory:
    def __init__(self, root, folders):
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        self.path = Path(root) / (stamp + '-' + uuid.uuid4().hex)
        self.folders = {role: Path(folder) for role, folder in folders.items()}

    def capture(self, phase):
        if phase not in ('before', 'after'):
            raise ValueError('Session history phase must be before or after')
        record = {'captured_utc': datetime.now(timezone.utc).isoformat(),
                  'phase': phase, 'files': [], 'errors': [], 'network': {}}
        for role, folder in self.folders.items():
            for name in EVIDENCE_FILES:
                source = folder / name
                target = self.path / phase / role / name
                try:
                    if not source.is_file():
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                    record['files'].append({'role': role, 'name': name,
                                            'source': str(source), 'bytes': target.stat().st_size})
                except OSError as error:
                    record['errors'].append(f'{source}: {error}')
            from old_native_network_diagnostics import summarize_log
            record['network'][role] = summarize_log(self.path / phase / role / 'Logs/error.log')
        try:
            target = self.path / phase / 'manifest.json'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(record, ensure_ascii=False, indent=2), 'utf-8')
        except OSError as error:
            record['errors'].append(f'{target}: {error}')
        if record['errors']:
            for error in record['errors']:
                print('Не удалось сохранить часть журнала сеанса:', error, flush=True)
        else:
            print(f'Журнал сеанса ({phase}): {self.path}', flush=True)
        return record
