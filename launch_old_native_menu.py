"""Open the original game's main menu with the cooperative LAN campaign UI.

The game owns discovery, hosting and joining through its native DirectPlay.
The launcher only prepares isolated files/settings and owns their lifetime.
"""
import argparse
import json
import os
import subprocess
import time

from old_native_installation import (MOD, build_fingerprint, cached_runtime, mark_installed,
                                     save_source, save_reloaded_source, source_root, validate_source,
                                     directplay_available)
from old_native_session_lock import NativeSessionBusyError, old_native_session_lock
from old_native_session_history import NativeSessionHistory
from old_native_localization import get_language, tr


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--two-windows', action='store_true',
                        help='Open two independent menus on this PC for manual create/join testing')
    parser.add_argument('--prepare-only', action='store_true', help='Prepare menu builds without launching')
    parser.add_argument('--source', help='Supported original game installation directory')
    reloaded = parser.add_mutually_exclusive_group()
    reloaded.add_argument('--reloaded-source', help='Optional installed Reloaded source for the two road missions')
    reloaded.add_argument('--without-reloaded', action='store_true', help='Use only the original campaign missions')
    parser.add_argument('--rebuild', action='store_true', help='Repair/rebuild generated files')
    parser.add_argument('--windowed', action='store_true', help='Use a window for this launch without changing preferences')
    parser.add_argument('--safe-video', action='store_true', help='Reset only display settings to windowed 800x600')
    parser.add_argument('--infinite-health', action='store_true',
                        help='Host enables infinite health for both heroes in this test session')
    parser.add_argument('--save', help='Host checkpoint (.as2coop.json); clients receive the host selection automatically')
    parser.add_argument('--log', help='Append diagnostics to a .log file inside this mod installation runtime directory')
    parser.add_argument('--language', choices=('en', 'ru'), help='Mod text language; both players must use the same language')
    args = parser.parse_args(argv)
    # Freeze this worker's selection before importing any game builders or
    # serving checkpoint/browser requests. Another launcher may change its UI.
    os.environ['AS2_COOP_LANGUAGE'] = args.language or get_language()
    if args.log:
        from contextlib import redirect_stdout, redirect_stderr
        from campaign_launcher import session_log_path
        path = session_log_path(args.log)
        path.parent.mkdir(exist_ok=True)
        with path.open('a', encoding='utf-8', buffering=1) as log:
            with redirect_stdout(log), redirect_stderr(log):
                return run(args)
    return run(args)


def run(args):
    processes = []
    try:
        with old_native_session_lock():
            source = save_source(args.source) if args.source else validate_source(source_root())
            if args.reloaded_source is not None or args.without_reloaded:
                save_reloaded_source(args.reloaded_source)
                # An explicit launch selection also overrides an inherited
                # development environment, before mission globals are imported.
                os.environ.pop('AS2_COOP_RELOADED_DIR', None)
            # Import builders only after both source directories are chosen.
            from old_native_runtime_settings import configure_runtime
            from old_native_process import close_owned
            from old_native_campaign_build import build
            roles = ('host', 'client') if args.two_windows else ('host',)
            history = NativeSessionHistory(MOD / 'runtime/session-history',
                {role: MOD / 'runtime' / ('old-game-' + role) for role in roles})
            history.capture('before')
            fingerprint = build_fingerprint()
            folders = []
            for role in roles:
                folder = None if args.rebuild else cached_runtime(role, source, fingerprint)
                if folder is None:
                    print(tr('Подготовка игровых файлов…', 'Preparing game files...'), flush=True)
                    folder = build(role)
                    mark_installed(folder, role, source, fingerprint)
                folders.append(folder)
            if args.prepare_only:
                if args.safe_video:
                    for role, folder in zip(roles, folders):
                        configure_runtime(role, folder, safe_video=True)
                print(tr('Установка готова. Оригинальная игра не изменена.', 'Installation ready. The original game is unchanged.'), flush=True)
                return 0
            if not directplay_available():
                raise RuntimeError(tr('Для сетевой игры включите компонент Windows: Устаревшие компоненты → DirectPlay.',
                                      'Enable the Windows feature Legacy Components > DirectPlay for network play.'))
            for role, folder in zip(roles, folders):
                configure_runtime(role, folder, force_windowed=args.two_windows or args.windowed,
                                  safe_video=args.safe_video, infinite_health=args.infinite_health)
            from old_native_checkpoints import CheckpointService
            checkpoints = CheckpointService(folders, MOD / 'saves/campaign', args.save)
            startup = subprocess.STARTUPINFO()
            startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 1
            try:
                for folder in folders:
                    processes.append(subprocess.Popen([str(folder / 'AlienShooter.exe')],
                                                      cwd=folder, startupinfo=startup))
                (MOD / 'native-campaign-menu-status.json').write_text(json.dumps({
                    'processes': {role: process.pid for role, process in zip(roles, processes)},
                    'runtime_directories': [str(folder) for folder in folders],
                    'native_network': True, 'automatic_input': False,
                    'language': get_language(),
                }, indent=2), 'utf-8')
                print('AS2_CAMPAIGN_OPENED', flush=True)
                print(tr('Сетевая кампания открыта. Выберите новую игру, сохранение или подключение. При загрузке сохранения персонажи восстанавливаются автоматически.',
                         'Co-op campaign opened. Choose a new game, a saved game or join a session. Loading a save restores both characters automatically.'), flush=True)
                while all(process.poll() is None for process in processes):
                    checkpoints.poll()
                    time.sleep(0.1)
                return next((process.returncode for process in processes
                             if process.returncode not in (None, 0)), 0)
            finally:
                try:
                    for process in reversed(processes):
                        close_owned(process)
                finally:
                    history.capture('after')
    except KeyboardInterrupt:
        return 0
    except (NativeSessionBusyError, OSError, ValueError, RuntimeError) as error:
        print('Campaign menu launch failed:', error, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
