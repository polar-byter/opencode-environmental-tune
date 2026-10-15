# Поясняющие GIF / Explainer GIFs

Русские схемы лежат в этой папке, английские — в [`en/`](en/). Имена файлов совпадают.
Russian diagrams live here, English ones in [`en/`](en/). File names match.

| Файл / File | О чём | What it shows | ~ |
| --- | --- | --- | --- |
| `01_master_chief_planning.gif` | Мастер Чиф читает TASK.md, AGENTS.md, currentsteps.md, README; решения, каркас, красные тесты | The Master Chief reads TASK.md, AGENTS.md, currentsteps.md, README; decisions, skeleton, red tests | 60 s |
| `02_delegation_review_dashboard.gif` | требования → delegate → исполнитель → inspect → ревью и возврат → accepted; STOP; дашборд; finish | requirements → delegate → executor → inspect → review and rework → accepted; STOP; dashboard; finish | 61 s |
| `03_project_setup.gif` | кит в проекте, `# EDIT` и `check`, источники моделей, конфигуратор, «Проверить связь», сохранение, два способа поставить задачу | kit in the project, `# EDIT` and `check`, model sources, configurator, Check connection, saving, two ways to give a task | 60 s |
| `04_lmstudio_openrouter.gif` | LM Studio: загруженная модель, выбор, надстройка; OpenRouter: каталог, фильтры, `:free`, «Ключ найден», `/connect`; группы токенов | LM Studio: loaded model, selection, overlay; OpenRouter: catalog, filters, `:free`, Key found, `/connect`; token groups | 67 s |
| `05_dashboard_controls.gif` | вкладки, «Сейчас в работе», настройки, пауза / продолжение / остановка / удаление, итог | tabs, Working now, settings, pause / resume / stop / delete, summary | 72 s |

Кадр 1200×675, GIF зациклены, данные — примеры. Подключены в
[README.md](../README.md), [README.en.md](../README.en.md),
[QUICKSTART.ru.md](../QUICKSTART.ru.md) и [QUICKSTART.en.md](../QUICKSTART.en.md).
Страница дашборда сейчас только на русском; в английских схемах её подписи переведены.

## Пересборка / Rebuild

Нужны Python и Pillow; шрифты Segoe UI / Consolas берутся из Windows.

```powershell
cd readme_gif/source
foreach ($f in 'gif1_planning','gif2_delegation','gif3_setup','gif4_models','gif5_dashboard') {
  py "$f.py"; $env:GIF_LANG = 'en'; py "$f.py"; Remove-Item Env:GIF_LANG
}
```

- `gifkit.py` — общие примитивы и сборка GIF; при `GIF_LANG=en` строки переводятся
  через `i18n_en.py`, а файлы пишутся в `en/`.
- Текст шагов задаётся в `STEPS` каждого скрипта; новые русские строки добавь
  в `i18n_en.py`. `py collect.py` перечисляет строки без перевода (должно быть 0).
