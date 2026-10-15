"""Player-facing installer/launcher. Frozen builds include Python and patch tools."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import uuid

from old_native_installation import MOD, BUNDLE, VERSION, source_root, validate_source
from old_native_localization import get_language, set_language, tr, guide_name


def worker_command(arguments):
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--session', *arguments]
    return [sys.executable, '-B', str(Path(__file__).resolve()), '--session', *arguments]


def session_log_path(value=None):
    """Keep each launch's diagnostics inside this installation's runtime."""
    runtime = (MOD / 'runtime').resolve()
    path = Path(value).resolve() if value else runtime / ('launch-' + uuid.uuid4().hex + '.log')
    if path.parent != runtime or path.suffix.lower() != '.log':
        raise ValueError(tr('Журнал запуска должен находиться в папке runtime мода и иметь расширение .log.',
                            'The launch log must be a .log file inside the mod runtime folder.'))
    return path


def installation_help(language=None):
    """Use the installation guide shipped alongside this particular release."""
    name = guide_name(language)
    for path in (MOD / name, BUNDLE / name):
        try:
            return path.read_text('utf-8-sig')
        except OSError:
            pass
    return tr(
        'Нужна полная поддерживаемая русская старая Alien Shooter 2. Выберите её папку '
        'с AlienShooter.exe и нажмите «Играть». Reloaded как основа не поддерживается.\n\n'
        'Язык меняет только тексты мода. У обоих игроков должны совпадать версия и язык '
        'мода. Для сети нужен компонент Windows DirectPlay. Две дополнительные карты '
        'включены; отдельная Reloaded не требуется.\n\n'
        'Полная инструкция INSTALL_RU.txt должна находиться рядом с лаунчером.',
        'A complete supported Russian OLD Alien Shooter 2 installation is required. '
        'Select its folder containing AlienShooter.exe and press PLAY. Reloaded is not '
        'a supported base game.\n\n'
        'Language changes mod-added text only. Both players must use the same mod '
        'version and language. Networking requires Windows DirectPlay. Two additional '
        'maps are included; no separate Reloaded installation is needed.\n\n'
        'The full INSTALL_EN.txt guide should be next to the launcher.', language)


def run_session(arguments):
    # A windowed PyInstaller worker has no Python stdout/stderr, even when its
    # native handles were redirected by Popen. Bind them before loading builders.
    import argparse
    from contextlib import redirect_stdout, redirect_stderr
    import traceback
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--log')
    options, arguments = parser.parse_known_args(arguments)
    path = session_log_path(options.log)
    path.parent.mkdir(exist_ok=True)
    with path.open('a', encoding='utf-8', buffering=1) as log:
        with redirect_stdout(log), redirect_stderr(log):
            try:
                from launch_old_native_menu import main as run
                return run(arguments)
            except Exception:
                traceback.print_exc()
                return 1


def main():
    if '--session' in sys.argv:
        return run_session(sys.argv[sys.argv.index('--session') + 1:])
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    root = tk.Tk()
    root.geometry(f'780x{max(580, min(780, root.winfo_screenheight() - 80))}')
    root.minsize(720, 580)
    root.configure(bg='#151a1c')
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', font=('Segoe UI', 10), background='#20282c', foreground='#edf0e8')
    style.configure('TFrame', background='#151a1c')
    style.configure('TLabel', background='#151a1c')
    style.configure('Muted.TLabel', foreground='#aab8bc', background='#151a1c')
    style.configure('TButton', padding=(16, 9), background='#343f43', borderwidth=0)
    style.map('TButton', background=[('active', '#46575b'), ('disabled', '#293135')],
              foreground=[('disabled', '#718085')])
    style.configure('Play.TButton', font=('Segoe UI', 13, 'bold'), background='#657840')
    style.map('Play.TButton', background=[('active', '#7b9251'), ('disabled', '#343f32')])
    style.configure('TEntry', fieldbackground='#283238', foreground='#f2f4ed', padding=7)
    style.configure('TCombobox', fieldbackground='#283238', foreground='#f2f4ed', padding=7)
    style.map('TCombobox', fieldbackground=[('readonly', '#283238')],
              foreground=[('readonly', '#f2f4ed')])
    root.option_add('*TCombobox*Listbox.background', '#283238')
    root.option_add('*TCombobox*Listbox.foreground', '#f2f4ed')
    style.configure('TCheckbutton', background='#151a1c', padding=(0, 6))
    style.map('TCheckbutton', background=[('active', '#151a1c')])
    style.configure('TNotebook', background='#151a1c', borderwidth=0)
    style.configure('TNotebook.Tab', padding=(20, 8), background='#293338')
    style.map('TNotebook.Tab', background=[('selected', '#46533c')])

    captions = []

    def caption(ru, en):
        variable = tk.StringVar(value=tr(ru, en))
        captions.append((variable, ru, en))
        return variable

    outer = ttk.Frame(root, padding=26)
    outer.pack(fill='both', expand=True)
    ttk.Label(outer, text='ALIEN SHOOTER 2', font=('Segoe UI', 24, 'bold')).pack(anchor='w')
    heading = ttk.Frame(outer)
    heading.pack(fill='x', pady=(3, 17))
    ttk.Label(heading, textvariable=caption('СОВМЕСТНАЯ КАМПАНИЯ  ·  LAN', 'COOPERATIVE CAMPAIGN  ·  LAN'),
              foreground='#b7cf8a', font=('Segoe UI', 11, 'bold')).pack(side='left')
    language_var = tk.StringVar(value={'en': 'English', 'ru': 'Русский'}[get_language()])
    language_select = ttk.Combobox(heading, textvariable=language_var, values=('English', 'Русский'),
                                  state='readonly', width=11)
    language_select.pack(side='right')
    notebook = ttk.Notebook(outer)
    notebook.pack(fill='both', expand=True)
    play_tab = ttk.Frame(notebook, padding=(18, 18))
    help_tab = ttk.Frame(notebook, padding=(18, 18))
    notebook.add(play_tab, text=tr('Играть', 'Play'))
    notebook.add(help_tab, text=tr('Установка и помощь', 'Installation and help'))
    settings_view = ttk.Frame(play_tab)
    settings_view.pack(fill='both', expand=True)
    settings_scroll = ttk.Scrollbar(settings_view, orient='vertical')
    settings_scroll.pack(side='right', fill='y')
    settings_canvas = tk.Canvas(settings_view, bg='#151a1c', highlightthickness=0,
                                yscrollcommand=settings_scroll.set)
    settings_canvas.pack(side='left', fill='both', expand=True)
    settings_scroll.configure(command=settings_canvas.yview)
    play = ttk.Frame(settings_canvas)
    settings_window = settings_canvas.create_window((0, 0), window=play, anchor='nw')
    play.bind('<Configure>', lambda event: settings_canvas.configure(scrollregion=settings_canvas.bbox('all')))
    settings_canvas.bind('<Configure>', lambda event: settings_canvas.itemconfigure(settings_window, width=event.width))
    ttk.Label(play, textvariable=caption('Старая Alien Shooter 2 — основная игра', 'Original OLD Alien Shooter 2 — base game'), font=('Segoe UI', 11, 'bold')).pack(anchor='w')
    ttk.Label(play, textvariable=caption('Выберите папку с AlienShooter.exe. Оригинальные файлы сохраняются.',
                                        'Select the folder containing AlienShooter.exe. Original files are preserved.'),
              style='Muted.TLabel').pack(anchor='w', pady=(3, 10))
    path_var = tk.StringVar(value=str(source_root()))
    path_row = ttk.Frame(play)
    path_row.pack(fill='x')
    entry = ttk.Entry(path_row, textvariable=path_var)
    entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
    browse = ttk.Button(path_row, textvariable=caption('Обзор…', 'Browse…'), command=lambda: choose())
    browse.pack(side='right')
    ttk.Label(play, textvariable=caption('Две дополнительные дорожные миссии уже включены.\nОтдельная установка Reloaded не нужна.',
                                        'Two additional road missions are included.\nNo separate Reloaded installation is needed.'),
              style='Muted.TLabel', wraplength=610).pack(anchor='w', pady=(12, 0))
    ttk.Label(play, textvariable=caption('Новая кампания, сохранения и подключение — в меню игры «Сетевая кампания».',
                                        'Start a campaign, load a save or join a game from the in-game “Co-op campaign” menu.'),
              style='Muted.TLabel', wraplength=610).pack(anchor='w', pady=(12, 0))
    ttk.Label(play, textvariable=caption('Графика, разрешение, звук и управление — в настройках самой игры.',
                                        'Change graphics, resolution, sound and controls in the game settings.'),
              style='Muted.TLabel', wraplength=610).pack(anchor='w', pady=(5, 6))
    two = tk.BooleanVar(value=False)
    ttk.Label(play, textvariable=caption('Язык меняет тексты мода; оригинальная игра остаётся русской.\nОбоим игрокам нужен одинаковый язык мода.',
                                        'Language changes mod-added text; the original game stays Russian.\nBoth players must select the same mod language.'),
              style='Muted.TLabel', wraplength=610).pack(anchor='w', pady=(5, 6))
    two_check = ttk.Checkbutton(play, variable=two, textvariable=caption('Два окна на этом компьютере для совместной проверки',
                                                                       'Two windows on this PC for cooperative testing'))
    two_check.pack(anchor='w')
    safe_video = tk.BooleanVar(value=False)
    safe_check = ttk.Checkbutton(play, variable=safe_video, textvariable=caption('Сбросить экран: окно 800×600', 'Reset display: 800×600 window'))
    safe_check.pack(anchor='w')
    infinite_health = tk.BooleanVar(value=False)
    health_check = ttk.Checkbutton(play, variable=infinite_health,
                                  textvariable=caption('Тест: бесконечное здоровье обоим игрокам (настройка хоста)',
                                                       'Test: infinite health for both players (host setting)'))
    health_check.pack(anchor='w')
    status_message = ['Первый запуск подготовит отдельную копию игры для мода.',
                      'The first launch prepares a separate game copy for the mod.']
    status = tk.StringVar(value=tr(*status_message))

    def show_status(ru, en):
        status_message[:] = [ru, en]
        status.set(tr(ru, en))
    ttk.Label(play_tab, textvariable=status, wraplength=620).pack(anchor='w', pady=(12, 5))
    bar = ttk.Progressbar(play_tab, mode='indeterminate')
    bar.pack(fill='x', pady=(5, 14))
    action_row = ttk.Frame(play_tab)
    action_row.pack(fill='x')
    start = ttk.Button(action_row, textvariable=caption('ИГРАТЬ', 'PLAY'), style='Play.TButton', command=lambda: begin(False))
    start.pack(side='left')
    install = ttk.Button(action_row, textvariable=caption('Установить / восстановить', 'Install / repair'), command=lambda: begin(True))
    install.pack(side='left', padx=12)
    ttk.Label(outer, textvariable=caption(VERSION + '  ·  Два игрока  ·  17 миссий  ·  Автосохранение',
                                          VERSION + '  ·  Two players  ·  17 missions  ·  Autosave'),
              style='Muted.TLabel').pack(anchor='w', pady=(13, 0))
    help_text = installation_help()
    help_scroll = ttk.Scrollbar(help_tab, orient='vertical')
    help_scroll.pack(side='right', fill='y')
    help_view = tk.Text(help_tab, wrap='word', bg='#151a1c', fg='#edf0e8',
                        font=('Segoe UI', 10), relief='flat', borderwidth=0,
                        yscrollcommand=help_scroll.set, padx=0, pady=0)
    help_view.insert('1.0', help_text)
    help_view.configure(state='disabled')
    help_view.pack(fill='both', expand=True)
    help_scroll.configure(command=help_view.yview)
    state = {'process': None, 'log': None, 'log_path': None, 'prepare': False}

    def refresh_language():
        root.title(tr('Alien Shooter 2 — Совместная кампания', 'Alien Shooter 2 — Cooperative Campaign'))
        for variable, ru, en in captions:
            variable.set(tr(ru, en))
        notebook.tab(play_tab, text=tr('Играть', 'Play'))
        notebook.tab(help_tab, text=tr('Установка и помощь', 'Installation and help'))
        status.set(tr(*status_message))
        help_view.configure(state='normal')
        help_view.delete('1.0', 'end')
        help_view.insert('1.0', installation_help())
        help_view.configure(state='disabled')

    def choose_language(event=None):
        previous = get_language()
        try:
            set_language({'English': 'en', 'Русский': 'ru'}[language_var.get()])
        except (OSError, ValueError) as error:
            language_var.set({'en': 'English', 'ru': 'Русский'}[previous])
            messagebox.showerror(tr('Язык мода', 'Mod language'), str(error), parent=root)
            return
        refresh_language()

    language_select.bind('<<ComboboxSelected>>', choose_language)
    refresh_language()

    def choose():
        selected = filedialog.askdirectory(parent=root, title=tr('Папка старой Alien Shooter 2', 'Original OLD Alien Shooter 2 folder'),
                                           initialdir=path_var.get() if Path(path_var.get()).is_dir() else str(MOD))
        if selected:
            path_var.set(selected)

    def begin(prepare):
        if state['process'] is not None:
            return
        try:
            source = validate_source(path_var.get())
            (MOD / 'runtime').mkdir(exist_ok=True)
            log_path = session_log_path()
            log = log_path.open('x', encoding='utf-8')
            arguments = ['--source', str(source), '--log', str(log_path), '--language', get_language()]
            if two.get():
                arguments.append('--two-windows')
            if safe_video.get():
                arguments.append('--safe-video')
            if infinite_health.get():
                arguments.append('--infinite-health')
            if prepare:
                arguments += ['--prepare-only', '--rebuild']
            startup = subprocess.STARTUPINFO()
            startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 0
            environment = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
            try:
                process = subprocess.Popen(worker_command(arguments), cwd=MOD, stdout=log, stderr=log,
                                           startupinfo=startup, env=environment)
            except Exception:
                log.close()
                raise
            state.update(process=process, log=log, log_path=log_path, prepare=prepare)
            for widget in (start, install, browse, entry, two_check, safe_check, health_check):
                widget.configure(state='disabled')
            language_select.configure(state='disabled')
            bar.start(15)
            show_status('Подготовка файлов. Первый запуск может занять несколько минут…',
                        'Preparing files. The first launch may take a few minutes…')
            root.after(500, poll)
        except (OSError, ValueError) as error:
            messagebox.showerror(tr('Запуск кампании', 'Launch campaign'), str(error), parent=root)

    def poll():
        process = state['process']
        code = process.poll()
        if code is None:
            try:
                text = state['log_path'].read_text('utf-8', errors='replace')
                if 'AS2_CAMPAIGN_OPENED' in text:
                    bar.stop()
                    show_status('Игра запущена. Это окно можно закрыть; игра продолжит работать.',
                                'The game is running. You may close this launcher; the game will keep running.')
            except OSError:
                pass
            root.after(1000, poll)
            return
        state['log'].close()
        state.update(process=None, log=None)
        bar.stop()
        for widget in (start, install, browse, entry, two_check, safe_check, health_check):
            widget.configure(state='normal')
        language_select.configure(state='readonly')
        if code:
            try:
                text = state['log_path'].read_text('utf-8', errors='replace')
            except OSError as error:
                text = tr('Не удалось прочитать журнал: ', 'Could not read the log: ') + str(error)
            relative_log = 'runtime/' + state['log_path'].name
            show_status('Не удалось запустить. Журнал: ' + relative_log, 'Launch failed. Log: ' + relative_log)
            messagebox.showerror(tr('Запуск кампании', 'Launch campaign'), '\n'.join(text.splitlines()[-10:]), parent=root)
        else:
            safe_video.set(False)
            if state['prepare']:
                show_status('Установка готова — можно играть.', 'Installation is ready — you can play.')
            else:
                show_status('Игра закрыта. Можно продолжить из автосохранения или начать заново.',
                            'The game has closed. Continue from an autosave or start a new campaign.')

    root.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
