"""A small EN/RU project setup wizard, reusing the existing model configurator."""
from pathlib import Path
import queue
import threading
import webbrowser

from . import installer, localization
from .configurator import app, icons
from .configurator.desktop import DesktopConfigurator

tk, ttk = app.tk, app.ttk
SOURCE = Path(__file__).resolve().parents[1]
PROMPT_EN = ('Create a local to-do application. I need to add tasks, choose a due date, '
             'mark them complete and filter by status. Keep data between restarts. '
             'Choose a simple stack, use SQLite for storage, and include a clear launch file. '
             'Design a readable interface. Follow the kit rules, create the plan and tests, '
             'delegate implementation to the configured workers and complete the whole plan. '
             'Show the final test results and explain how to run the application.')
PROMPT_RU = ('Создай локальное приложение для списка дел: добавление задачи, дата выполнения, '
             'отметка о выполнении и фильтр по статусу. Данные должны сохраняться между запусками. '
             'Выбери простой стек, храни данные в SQLite и подготовь понятный файл запуска. '
             'Сделай читаемый интерфейс. Следуй правилам кита, составь план и тесты, '
             'поручай реализацию настроенным исполнителям и выполни весь план. '
             'В конце покажи результаты тестов и объясни, как запустить приложение.')


class InstallerWindow:
    def __init__(self, window, source=SOURCE, *, language=None):
        self.window, self.source = window, Path(source)
        self.language = language or localization.system_language()
        self.labels, self.results = [], queue.Queue()
        self.busy = self.closed = False
        self.project = self.configuration = self.config_window = None
        self.prepared = False
        self.desktop = installer.find_desktop()
        self.path = tk.StringVar(value=str(Path.home() / 'Projects' / 'my-project'))
        self.auto_open = tk.BooleanVar(value=True)
        self.status = tk.StringVar()
        self.build()
        self.localize()
        self.refresh_desktop()
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.poll_id = window.after(80, self.poll)

    def tr(self, key, **values):
        return localization.text(key, self.language, **values)

    def label(self, widget, key):
        self.labels.append((widget, key))
        return widget

    def build(self):
        self.window.geometry('840x770')
        self.window.minsize(740, 740)
        self.window.configure(background='#f2f5fa')
        self.images = icons.application(self.window)
        style = ttk.Style(self.window)
        style.theme_use('clam')
        style.configure('Installer.TFrame', background='#f2f5fa')
        style.configure('Installer.TLabel', background='#f2f5fa', foreground='#17243b', font=('Segoe UI', 10))
        style.configure('InstallerTitle.TLabel', background='#f2f5fa', foreground='#17243b', font=('Segoe UI', 22, 'bold'))
        style.configure('InstallerStep.TLabel', background='#f2f5fa', foreground='#17243b', font=('Segoe UI', 12, 'bold'))
        style.configure('Installer.TButton', padding=(10, 7))
        style.configure('InstallerPrimary.TButton', padding=(14, 10), background='#2563eb', foreground='white')
        style.map('InstallerPrimary.TButton', background=[('disabled', '#a1b7e6'), ('active', '#1d4ed8')])
        frame = ttk.Frame(self.window, style='Installer.TFrame', padding=24)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(0, weight=1)
        header = ttk.Frame(frame, style='Installer.TFrame')
        header.grid(row=0, column=0, sticky='ew')
        header.columnconfigure(0, weight=1)
        self.label(ttk.Label(header, style='InstallerTitle.TLabel', wraplength=560), 'Create your OpenCode project').grid(row=0, column=0, sticky='w')
        self.language_choice = tk.StringVar(value='Русский' if self.language == 'ru' else 'English')
        combo = ttk.Combobox(header, textvariable=self.language_choice, values=('English', 'Русский'), state='readonly', width=9)
        combo.grid(row=0, column=1, sticky='e', padx=(8, 0))
        combo.bind('<<ComboboxSelected>>', self.change_language)
        self.label(ttk.Label(frame, style='Installer.TLabel', wraplength=760),
                   'Find Desktop → choose a folder → configure models → start your first task.').grid(row=1, column=0, sticky='w', pady=(5, 16))
        self.label(ttk.Label(frame, style='InstallerStep.TLabel'), '1. OpenCode Desktop').grid(row=2, column=0, sticky='w')
        self.desktop_status = ttk.Label(frame, style='Installer.TLabel', wraplength=760)
        self.desktop_status.grid(row=3, column=0, sticky='w', pady=5)
        actions = ttk.Frame(frame, style='Installer.TFrame')
        actions.grid(row=4, column=0, sticky='w')
        for label, command in [('Download OpenCode', lambda: webbrowser.open(installer.DOWNLOAD_URL)),
                               ('Check again', self.refresh_desktop), ('Choose application…', self.choose_application)]:
            self.label(ttk.Button(actions, command=command, style='Installer.TButton'), label).pack(side='left', padx=(0, 7))
        self.label(ttk.Label(frame, style='InstallerStep.TLabel'), '2. Project folder').grid(row=5, column=0, sticky='w', pady=(20, 5))
        folder = ttk.Frame(frame, style='Installer.TFrame')
        folder.grid(row=6, column=0, sticky='ew')
        folder.columnconfigure(0, weight=1)
        self.path_entry = ttk.Entry(folder, textvariable=self.path, font=('Segoe UI', 11))
        self.path_entry.grid(row=0, column=0, sticky='ew', ipady=6)
        self.browse = self.label(ttk.Button(folder, command=self.choose_folder, style='Installer.TButton'), 'Choose folder…')
        self.browse.grid(row=0, column=1, padx=(8, 0))
        self.label(ttk.Label(frame, style='Installer.TLabel', wraplength=760),
                   'You can enter a new path. Missing folders are created for you. Existing project files are preserved.').grid(row=7, column=0, sticky='w', pady=6)
        self.label(ttk.Label(frame, style='InstallerStep.TLabel'), '3. Install the kit and choose models').grid(row=8, column=0, sticky='w', pady=(15, 5))
        self.label(ttk.Label(frame, style='Installer.TLabel', wraplength=760),
                   'The next window configures the Chief, executors and Bug Fixer. Click Prepare OpenCode there when ready.').grid(row=9, column=0, sticky='w')
        self.open_check = self.label(ttk.Checkbutton(frame, variable=self.auto_open), 'Open OpenCode after model setup')
        self.open_check.grid(row=10, column=0, sticky='w', pady=6)
        self.primary = ttk.Button(frame, command=self.next_step, style='InstallerPrimary.TButton')
        self.primary.grid(row=11, column=0, sticky='ew', pady=(6, 3))
        self.status_label = ttk.Label(frame, textvariable=self.status, style='Installer.TLabel', wraplength=760)
        self.status_label.grid(row=12, column=0, sticky='ew', pady=(5, 8))
        self.label(ttk.Label(frame, style='InstallerStep.TLabel'), '4. Your first task').grid(row=13, column=0, sticky='w', pady=(4, 4))
        self.prompt = tk.Text(frame, height=5, wrap='word', font=('Segoe UI', 10), relief='solid', borderwidth=1, padx=8, pady=7)
        self.prompt.insert('1.0', PROMPT_RU if self.language == 'ru' else PROMPT_EN)
        self.prompt.grid(row=14, column=0, sticky='nsew')
        frame.rowconfigure(14, weight=1)
        footer = ttk.Frame(frame, style='Installer.TFrame')
        footer.grid(row=15, column=0, sticky='ew', pady=(9, 0))
        self.label(ttk.Button(footer, command=self.copy_prompt, style='Installer.TButton'), 'Copy prompt').pack(side='left')
        self.label(ttk.Button(footer, command=self.copy_folder, style='Installer.TButton'), 'Copy folder path').pack(side='left', padx=8)
        self.settings_button = self.label(ttk.Button(footer, command=self.configure_models, style='Installer.TButton'), 'Model settings')
        self.settings_button.pack(side='right')
        def resize(event):
            for widget in (self.desktop_status, self.status_label):
                widget.configure(wraplength=max(300, event.width - 48))
            for widget, key in self.labels:
                if isinstance(widget, ttk.Label) and widget.cget('wraplength'):
                    widget.configure(wraplength=max(300, event.width - (170 if widget.master == header else 48)))
        self.window.bind('<Configure>', lambda event: resize(event) if event.widget == self.window else None)

    def localize(self):
        self.window.title(self.tr('Project setup — OpenCode Kit'))
        for widget, key in self.labels:
            widget.configure(text=self.tr(key))
        self.primary.configure(text=self.tr('Open project in OpenCode' if self.prepared else
                                           'Configure project models' if self.project else 'Create project and configure models'))
        self.primary.state(['disabled'] if self.busy or not self.desktop else ['!disabled'])
        self.settings_button.state(['!disabled'] if self.project and not self.busy else ['disabled'])
        self.desktop_status.configure(text=self.tr('Desktop found: {path}', path=self.desktop.application) if self.desktop else
                                      self.tr('Desktop not found. Install it, then click Check again.'))

    def change_language(self, event=None):
        before = PROMPT_RU if self.language == 'ru' else PROMPT_EN
        self.language = 'ru' if self.language_choice.get() == 'Русский' else 'en'
        if self.prompt.get('1.0', 'end-1c') == before:
            self.prompt.delete('1.0', 'end')
            self.prompt.insert('1.0', PROMPT_RU if self.language == 'ru' else PROMPT_EN)
        self.localize()
        self.status.set('')

    def refresh_desktop(self):
        self.desktop = installer.find_desktop()
        self.localize()

    def choose_application(self):
        from tkinter import filedialog
        value = filedialog.askopenfilename(parent=self.window, title=self.tr('Choose OpenCode Desktop application'))
        if value:
            found = installer.desktop_from_path(Path(value))
            if found:
                self.desktop = found
                self.localize()
            else:
                self.error(self.tr('Choose the Desktop application, not opencode-cli. Its bundled CLI must be installed too.'))

    def choose_folder(self):
        from tkinter import filedialog
        value = filedialog.askdirectory(parent=self.window, title=self.tr('Choose a project folder'), mustexist=False)
        if value:
            self.path.set(value)

    def next_step(self):
        if self.busy:
            return
        if self.prepared:
            self.open_desktop()
        elif self.project:
            self.configure_models()
        elif self.desktop:
            self.busy = True
            self.localize()
            self.status.set(self.tr('Creating the folder and copying the kit…'))
            destination = self.path.get()
            def work():
                try:
                    result = installer.install_project(self.source, destination)
                    self.results.put(('installed', result))
                except (OSError, ValueError) as error:
                    self.results.put(('error', str(error) if isinstance(error, installer.InstallError) else
                                      'Could not write the project files. Check the folder permissions and free disk space.'))
            threading.Thread(target=work, daemon=True).start()

    def poll(self):
        while not self.results.empty():
            kind, value = self.results.get_nowait()
            self.busy = False
            if kind == 'error':
                self.error(self.tr(value))
            else:
                self.project = Path(value['project'])
                self.path_entry.state(['disabled'])
                self.browse.state(['disabled'])
                try:
                    localization.save_language(self.project, self.language)
                except OSError:
                    self.error(self.tr('Could not save the interface language. The kit is installed; model setup can continue.'))
                self.status.set(self.tr('Kit installed. Choose models in the settings window.'))
                self.configure_models()
            self.localize()
        if not self.closed:
            self.poll_id = self.window.after(80, self.poll)

    def configure_models(self):
        if not self.project or self.busy:
            return
        if self.config_window and self.config_window.winfo_exists():
            self.config_window.lift()
            return
        self.config_window = tk.Toplevel(self.window)
        self.config_window.transient(self.window)
        self.configuration = DesktopConfigurator(self.config_window, self.project,
                                                 language=self.language, on_prepared=self.configured)

    def configured(self):
        self.prepared = True
        self.configuration.close()
        self.config_window = None
        self.localize()
        self.status.set(self.tr('Models prepared. Copy the example prompt and send it in a new build chat.'))
        if self.auto_open.get():
            self.open_desktop()

    def open_desktop(self):
        if not self.project or not self.prepared or not self.desktop:
            return
        try:
            installer.open_project(self.desktop, self.project)
            self.status_label.configure(foreground='#187047')
            self.status.set(self.tr('Opening request sent to Desktop. If the folder is not selected, use Open Project and paste its path. A new API key may require fully restarting Desktop first.'))
        except (OSError, ValueError) as error:
            self.error(self.tr(str(error)) if isinstance(error, installer.InstallError) else self.tr('Could not launch Desktop. Check the application path and try again.'))

    def copy_prompt(self):
        self.window.clipboard_clear()
        self.window.clipboard_append(self.prompt.get('1.0', 'end-1c'))
        self.status.set(self.tr('Prompt copied. Paste it into a new OpenCode build chat. Nothing has been sent to a model.'))

    def copy_folder(self):
        self.window.clipboard_clear()
        self.window.clipboard_append(str(self.project) if self.project else self.path.get())
        self.status.set(self.tr('Folder path copied. In Desktop choose Open Project and paste this path.'))

    def error(self, message):
        self.status_label.configure(foreground='#b42338')
        self.status.set(message)
        self.localize()

    def close(self):
        if self.busy or (self.configuration and self.configuration.preparing):
            self.status.set(self.tr('Wait for the current setup step to finish before closing.'))
            return
        self.closed = True
        self.window.after_cancel(self.poll_id)
        if self.config_window and self.config_window.winfo_exists():
            self.configuration.close()
        self.window.destroy()


def main():
    if tk is None:
        print('Python with tkinter is required. See https://www.python.org/downloads/')
        return 1
    window = tk.Tk()
    InstallerWindow(window)
    window.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
