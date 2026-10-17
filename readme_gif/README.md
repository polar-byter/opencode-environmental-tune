# Поясняющие GIF / Explainer GIFs

Русские схемы лежат в этой папке, английские — в [`en/`](en/). Имена файлов совпадают.
Russian diagrams live here, English ones in [`en/`](en/). File names match.

| Файл / File | О чём | What it shows | ~ |
| --- | --- | --- | --- |
| `01_install.gif` | Мастер установки: Desktop, папка проекта, кит и модели, первое задание | Setup wizard: Desktop, project folder, kit and models, first prompt | 33 s |
| `01_install_live.gif` | Мастер установки и окно моделей, запись экрана | Setup wizard and model window, screen capture | 34 s |
| `02_team.gif` | Роли: Мастер Чиф, исполнители, исправитель ошибок, контроллер, журнал и дашборд | Roles: Master Chief, executors, Bug Fixer, controller, journal and dashboard | 33 s |
| `03_plan.gif` | Как Мастер Чиф готовит работу: задача, чтение, решения, заготовки, тесты, старт | How the Master Chief prepares: task, reading, decisions, skeleton, tests, start | 36 s |
| `04_parallel.gif` | Несколько исполнителей в отдельных копиях, сторож, проверка и перенос по одному | Several executors in separate copies, watchdog, review and one-by-one integration | 42 s |
| `05_bugfixer.gif` | Когда зовут исправителя ошибок, когда нет, и что бывает при STOP | When the Bug Fixer is called, when not, and what STOP means | 35 s |
| `06_final.gif` | Финал: проверка интерфейса Мастер Чифом, полный набор тестов, отчёт, файл запуска | The finish: UX/UI review, full test suite, report, launch file | 30 s |
| `07_models.gif` | Модели ролей, число исполнителей и лимиты, исправитель, каталог OpenRouter, ключи | Role models, executor count and limits, Bug Fixer, OpenRouter catalog, keys | 36 s |
| `08_dashboard.gif` | Дашборд: каждый исполнитель, попытки, токены «≥», пауза, итог, язык EN/RU | Dashboard: each executor, attempts, "≥" tokens, pause, summary, EN/RU | 37 s |

Кадр 1200×675, GIF зациклены, данные — примеры. Подключены в
[README.md](../README.md), [README.en.md](../README.en.md),
[QUICKSTART.ru.md](../docs/user/QUICKSTART.ru.md) и [QUICKSTART.en.md](../docs/user/QUICKSTART.en.md).
Подписи интерфейса совпадают с реальными: дашборд и мастер установки — из
`kit/locales/ru.json`, окно моделей — из `kit/configurator/i18n.py`.

### Первая версия схем / First version

Подробные схемы последовательного процесса (один исполнитель, до появления
контроллера и исправителя) сохранены рядом; в документацию сейчас вставлены
схемы из таблицы выше. Detailed diagrams of the earlier sequential flow are kept too.

| Файл / File | О чём |
| --- | --- |
| `01_master_chief_planning.gif` | Мастер Чиф читает документы, решает, пишет каркас и красные тесты |
| `02_delegation_review_dashboard.gif` | requirements → delegate → inspect → ревью и возврат → accepted; STOP; finish |
| `03_project_setup.gif` | Ручное подключение кита, `# EDIT`, `check`, конфигуратор, два способа поставить задачу |
| `04_lmstudio_openrouter.gif` | LM Studio и OpenRouter подробно: выбор загруженной модели, каталог, ключ, `/connect` |
| `05_dashboard_controls.gif` | Вкладки дашборда, пауза / продолжение / остановка / удаление |

Скрипты первой версии: `gif1_planning.py` … `gif5_dashboard.py`.

## Пересборка / Rebuild

Нужны Python и Pillow; шрифты Segoe UI / Consolas / Segoe UI Symbol берутся из Windows.

```powershell
cd readme_gif/source
foreach ($f in 's01_install','s02_team','s03_plan','s04_parallel','s05_bugfixer','s06_final','s07_models','s08_dashboard') {
  py "$f.py"; $env:GIF_LANG = 'en'; py "$f.py"; Remove-Item Env:GIF_LANG
}
```

- `gifkit.py` — общие примитивы (карточки, «аватары» ролей, стрелки, подписи шагов)
  и сборка GIF; при `GIF_LANG=en` строки переводятся через `i18n_en.py`, а файлы
  пишутся в `en/`.
- Текст шагов задаётся в `STEPS` каждого скрипта `s0*.py`; новые русские строки
  добавь в `i18n_en.py`. `py collect.py` перечисляет строки без перевода (должно быть 0).
- `py sheet.py <модуль> <out.png>` — лист последних кадров всех шагов для просмотра.
- `capture_installer.py` + `build_installer_gif.py` — запись экрана мастера
  (установка во временную папку, Desktop не запускается) и сборка `01_install_live.gif`:
  `py capture_installer.py ru <папка>` → `py build_installer_gif.py ru <папка>` (и то же с `en`).
- `habr_clips.py <папка черновиков>` — короткие клипы и обложки для черновиков статей.
  Черновики лежат в Obsidian: `ИИ агенты/Мультиагенты. Opencode/Хабр. Черновики статей`.
