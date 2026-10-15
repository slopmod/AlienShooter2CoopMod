"""Exclusive lifetime lock for the shared old-game-host/client runtime copies."""
from contextlib import contextmanager
from pathlib import Path
import os


from old_native_installation import MOD
from old_native_localization import tr
LOCK_PATH = MOD / "runtime" / "old-native-session.lock"


class NativeSessionBusyError(RuntimeError):
    """Another cooperating launcher or probe owns the old-game directories."""


@contextmanager
def old_native_session_lock():
    """Hold from before build until all owned game children have been closed.

    Nonblocking Windows byte-range locking avoids waiting behind an interactive
    game. The OS releases the lock when its owning Python process exits; a stale
    lock file therefore does not prevent a future launch. Never unlink the file.
    """
    if os.name != "nt":
        raise OSError(tr('Для запуска оригинальной Alien Shooter 2 нужна Windows.',
                         'The original Alien Shooter 2 launcher requires Windows.'))
    import msvcrt

    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a+b", buffering=0) as stream:
        if os.fstat(stream.fileno()).st_size == 0:
            stream.write(b"\0")
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise NativeSessionBusyError(
                tr('Кампания уже запущена или её игровые файлы используются проверкой. '
                   'Закройте текущую сессию перед новым запуском.',
                   "The native campaign is already running, or another probe is "
                "using its runtime copies. Close that session before starting "
                "a new one.")
            ) from error
        try:
            yield LOCK_PATH
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


# Short alias for harnesses that already distinguish old and modern runtimes.
native_session_lock = old_native_session_lock
