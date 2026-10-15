"""OpenRouter storefront, sharing the desktop worker queue and saved-form contract."""
from datetime import datetime, timedelta, timezone
import threading
import webbrowser
from urllib.parse import quote

from . import app, i18n, openrouter, workflow

tk, ttk = app.tk, app.ttk


class CatalogTab:
    def __init__(self, owner):
        self.owner = owner
        self.models, self.by_id = [], {}
        self.choices = []
        self.busy, self.loaded, self.failed = False, False, False
        self.query = tk.StringVar()
        self.scope = tk.StringVar(value='For coding')
        self.tariff = tk.StringVar(value='All prices')
        self.sort = tk.StringVar(value='Free to paid')
        self.tools = tk.BooleanVar(value=True)
        self.target = tk.StringVar(value='exec')
        self.info = owner.translator.var('The catalog loads when this tab is opened. No API key is needed to browse.')
        self.detail = owner.translator.var('Choose a role, then click a model to fill in its own API settings.')
        self.count = owner.translator.var()
        self.page = ttk.Frame(owner.notebook, style='Card.TFrame', padding=16)
        self.page.columnconfigure(0, weight=1)
        self.page.rowconfigure(4, weight=1)
        owner.notebook.add(self.page, text='OpenRouter · catalog')
        self.build()
        for variable in (self.query, self.scope, self.tariff, self.sort, self.tools):
            variable.trace_add('write', lambda *args: self.render())
        owner.notebook.bind('<<NotebookTabChanged>>', self.opened, add='+')

    def build(self):
        title = ttk.Frame(self.page, style='Card.TFrame')
        title.grid(row=0, column=0, sticky='ew')
        title.columnconfigure(0, weight=1)
        ttk.Label(title, text='OpenRouter models', style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        self.refresh_button = ttk.Button(title, text='Refresh prices', command=self.refresh)
        self.refresh_button.grid(row=0, column=1)
        ttk.Label(self.page, text='USD per 1M tokens: input and output separately. Base catalog rates, excluding cache and special conditions.', style='Hint.TLabel', wraplength=800).grid(
                      row=1, column=0, sticky='w', pady=(6, 10))
        filters = ttk.Frame(self.page, style='Card.TFrame')
        filters.grid(row=2, column=0, sticky='ew')
        filters.columnconfigure(1, weight=1)
        ttk.Label(filters, text='Search', style='Card.TLabel').grid(row=0, column=0, padx=(0, 8))
        ttk.Entry(filters, textvariable=self.query).grid(row=0, column=1, sticky='ew')
        self.choice(filters, self.scope, ('For coding', 'All text models'), width=18).grid(row=0, column=2, padx=(8, 0))
        self.choice(filters, self.tariff, ('All prices', 'Free models', 'Paid models'), width=15).grid(row=0, column=3, padx=(8, 0))
        ttk.Checkbutton(filters, text='Tool support only', variable=self.tools).grid(
            row=1, column=0, columnspan=2, sticky='w', pady=(8, 0))
        self.choice(filters, self.sort, ('Free to paid', 'By input price', 'By output price', 'By context', 'By name'), width=28).grid(
                         row=1, column=2, columnspan=2, sticky='e', pady=(8, 0))
        target_bar = ttk.Frame(self.page, style='Card.TFrame')
        target_bar.grid(row=3, column=0, sticky='ew', pady=(12, 8))
        ttk.Label(target_bar, text='Assign to:', style='Card.TLabel').pack(side='left', padx=(0, 12))
        for role in ('exec', 'master_chief', 'bug_fixer'):
            ttk.Radiobutton(target_bar, text=workflow.ROLE_NAMES[role], variable=self.target, value=role,
                            command=self.assign).pack(side='left', padx=(0, 20))
        ttk.Label(target_bar, textvariable=self.count, style='Hint.TLabel').pack(side='right')
        table = ttk.Frame(self.page, style='Card.TFrame')
        table.grid(row=4, column=0, sticky='nsew')
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        columns = ('model', 'tariff', 'input', 'output', 'context', 'tools')
        self.tree = ttk.Treeview(table, columns=columns, show='headings', selectmode='browse', height=6)
        settings = (('model', 'Model · API ID', 300, 'w'), ('tariff', 'Pricing', 95, 'w'),
                    ('input', 'Input $/1M', 90, 'e'), ('output', 'Output $/1M', 90, 'e'),
                    ('context', 'Context', 85, 'e'), ('tools', 'Tools', 100, 'center'))
        self.column_labels = {column: title for column, title, width, anchor in settings}
        for column, title, width, anchor in settings:
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width, minwidth=width if column != 'model' else 230,
                             stretch=column == 'model', anchor=anchor)
        style = ttk.Style(self.page)
        style.configure('Treeview', rowheight=28, background='white', fieldbackground='white', borderwidth=0)
        style.configure('Treeview.Heading', padding=(6, 8), background='#e7edf7')
        self.tree.tag_configure('free', foreground='#187247')
        self.tree.grid(row=0, column=0, sticky='nsew')
        vertical = ttk.Scrollbar(table, orient='vertical', command=self.tree.yview)
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal = ttk.Scrollbar(table, orient='horizontal', command=self.tree.xview)
        horizontal.grid(row=1, column=0, sticky='ew')
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.bind('<<TreeviewSelect>>', lambda event: self.describe())
        self.tree.bind('<ButtonRelease-1>', self.clicked)
        self.tree.bind('<Return>', lambda event: self.assign())
        self.tree.bind('<space>', lambda event: self.assign())
        detail = ttk.Label(self.page, textvariable=self.detail, style='Hint.TLabel', wraplength=800, justify='left')
        detail.grid(row=5, column=0, sticky='ew', pady=(8, 6))
        buttons = ttk.Frame(self.page, style='Card.TFrame')
        buttons.grid(row=6, column=0, sticky='ew')
        self.form_button = ttk.Button(buttons, text='Role settings', command=self.go_to_role, state='disabled')
        self.form_button.pack(side='left')
        self.model_button = ttk.Button(buttons, text='Model page', command=self.open_model, state='disabled')
        self.model_button.pack(side='left', padx=8)
        info_label = ttk.Label(self.page, textvariable=self.info, style='Hint.TLabel', wraplength=800, justify='left')
        info_label.grid(row=7, column=0, sticky='ew', pady=(8, 0))
        self.page.bind('<Configure>', lambda event: (detail.configure(wraplength=max(400, event.width - 32)),
                                                   info_label.configure(wraplength=max(400, event.width - 32))))

    def choice(self, parent, variable, values, **options):
        display = tk.StringVar()
        combo = ttk.Combobox(parent, textvariable=display, state='readonly', **options)
        self.choices.append((combo, variable, display, values))
        combo.bind('<<ComboboxSelected>>', lambda event: variable.set(values[combo.current()]))
        return combo

    def localize(self):
        for combo, variable, display, values in self.choices:
            combo['values'] = tuple(self.owner.tr(value) for value in values)
            combo.current(values.index(variable.get()))
        for column, source in self.column_labels.items():
            self.tree.heading(column, text=self.owner.tr(source))
        self.render(preserve=True)

    def opened(self, event=None):
        if self.owner.notebook.select() != str(self.page) or self.loaded or self.busy or self.failed:
            return
        snapshot = openrouter.cached(self.owner.root)
        if snapshot:
            self.receive(snapshot, cached=True)
        self.refresh()

    def refresh(self):
        if self.busy:
            return
        self.busy = True
        self.refresh_button.state(['disabled'])
        self.info.set([i18n.text('Showing the previous catalog. ') if self.models else '',
                       i18n.text('Updating prices from OpenRouter…')])

        def work():
            try:
                snapshot = openrouter.fetch(self.owner.root)
            except Exception:
                snapshot = None
            self.owner.results.put(('catalog', snapshot))

        threading.Thread(target=work, daemon=True).start()

    def receive(self, snapshot, cached=False):
        if not cached:
            self.busy = False
            self.refresh_button.state(['!disabled'])
        if snapshot is None:
            self.failed = True
            self.info.set([i18n.text('Could not refresh the catalog. Check your connection and click Refresh prices.'),
                           i18n.text(' Previous data is shown; prices may have changed.') if self.models else ''])
            return
        try:
            models = openrouter.parse_models(snapshot['payload'], set(snapshot['programming_ids']))
            updated = datetime.fromtimestamp(snapshot['fetched_at'], timezone(timedelta(hours=10))).strftime('%d.%m.%Y %H:%M')
        except (ValueError, KeyError, TypeError, OverflowError, OSError):
            self.receive(None)
            return
        self.models, self.by_id = models, {model.id: model for model in models}
        self.loaded, self.failed = True, False
        warning = snapshot.get('warning', '')
        # Older caches may contain the original Russian warning. Only known messages
        # are localized; remote model names and descriptions remain untouched.
        warning = {value: key for key, value in i18n.RU.items()}.get(warning, warning)
        self.info.set([i18n.text('Cache · ') if cached else '',
                       i18n.text('Updated {time} (Vladivostok). ', time=updated),
                       i18n.text('Connect to the internet for fresh prices. ') if cached else '',
                       i18n.text('For coding: OpenRouter programming picks and code mentions in descriptions. '),
                       i18n.text(warning)])
        self.render()

    def render(self, preserve=False):
        selected = self.tree.selection() if preserve else ()
        rows = openrouter.select_models(self.models, self.query.get(),
                    scope='coding' if self.scope.get() == 'For coding' else 'all',
                    tariff={'Free models': 'free', 'Paid models': 'paid'}.get(self.tariff.get(), 'all'),
                    tools_only=self.tools.get(), sort={'By input price': 'input', 'By output price': 'output',
                    'By context': 'context', 'By name': 'name'}.get(self.sort.get(), 'price'))
        self.tree.delete(*self.tree.get_children())
        for model in rows:
            self.tree.insert('', 'end', iid=model.id, values=(model.id, self.owner.tr(model.tariff),
                    openrouter.money(model.input_price), openrouter.money(model.output_price),
                    f'{model.context:,}'.replace(',', ' ') if model.context else '—',
                    self.owner.tr('Yes') if model.tools is True else self.owner.tr('No') if model.tools is False else '—'),
                    tags=('free',) if model.tariff == 'Free' else ())
        self.count.set('{shown} of {total}', shown=len(rows), total=len(self.models))
        self.form_button.state(['disabled'])
        self.model_button.state(['disabled'])
        self.detail.set('Select a role and click a row. Enter also assigns the model. Save changes separately.')
        if selected and self.tree.exists(selected[0]):
            self.tree.selection_set(selected[0])
            self.tree.see(selected[0])
            self.describe()

    def selected(self):
        selection = self.tree.selection()
        return self.by_id.get(selection[0]) if selection else None

    def describe(self):
        model = self.selected()
        if model is None:
            return
        parts = [i18n.text('{name} · {kind}', name=model.name, kind=i18n.text(model.coding or 'Text model'))]
        role = self.target.get()
        if self.owner.vars[role + '_model'].get() == model.id and self.owner.vars[role + '_source'].get() == 'api':
            parts = [i18n.text('{role} ← {name}. Open role settings to save.',
                              role=i18n.text(workflow.ROLE_NAMES[role]), name=model.name)]
        parts.append(i18n.text('\nCache: read {read}, write {write} per 1M.',
                              read=openrouter.money(model.cache_read), write=openrouter.money(model.cache_write)))
        if model.request_price:
            parts.append(i18n.text(' Per request: {price}.', price=openrouter.money(model.request_price, per_million=False)))
        if model.conditional:
            parts.append(i18n.text(' Conditional rates apply for time or context length; see the model page.'))
        if model.tools is not True:
            parts.append(i18n.text(' Tool support is not declared; agents require it.'))
        self.detail.set(parts)
        self.form_button.state(['!disabled'])
        self.model_button.state(['!disabled'])

    def clicked(self, event):
        if self.tree.identify_region(event.x, event.y) not in ('cell', 'tree'):
            return
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self.assign()

    def assign(self):
        model = self.selected()
        if model is None:
            return
        self.owner.choose_openrouter(model.id, self.target.get())
        self.describe()

    def go_to_role(self):
        if self.selected() is not None:
            self.assign()
            self.owner.notebook.select(self.owner.pages[self.target.get()])
            self.owner.canvases[self.target.get()].yview_moveto(0)

    def open_model(self):
        model = self.selected()
        if model:
            webbrowser.open('https://openrouter.ai/' + quote(model.id, safe='/'))
