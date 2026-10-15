# Поясняющие GIF для README

| Файл | О чём | Длительность |
| --- | --- | --- |
| [01_master_chief_planning.gif](01_master_chief_planning.gif) | Как Мастер Чиф читает TASK.md / AGENTS.md / currentsteps.md / README, принимает решения, пишет каркас и красные тесты | ~60 с |
| [02_delegation_review_dashboard.gif](02_delegation_review_dashboard.gif) | requirements → delegate → исполнитель → inspect → ревью и возврат → accepted; лимиты STOP; что видно в дашборде; finish и отчёт | ~61 с |
| [03_project_setup.gif](03_project_setup.gif) | Кит в новом проекте, разделы `# EDIT` и `check`, источники моделей, конфигуратор (OpenCode-модель, свой API), сохранение и подготовка, два способа поставить задачу | ~57 с |
| [04_lmstudio_openrouter.gif](04_lmstudio_openrouter.gif) | LM Studio: загруженный экземпляр, выбор, надстройка, check_env; OpenRouter: каталог, фильтры, подстановка `:free`, ключ, `/connect`; группы токенов | ~66 с |
| [05_dashboard_controls.gif](05_dashboard_controls.gif) | Вкладки дашборда, «Сейчас в работе», настройки моделей, пауза / продолжение / остановка / удаление, итог после finish | ~72 с |

Размер кадра 1200×675, GIF зациклены. Данные в таблицах и счётчиках — примеры. Все пять GIF подключены к основному
[README проекта](../README.md) в раскрывающихся разделах «Как пользоваться».
Актуальные поля ключа и проверка связи описаны в
[руководстве конфигуратора](../kit/configurator/UX.ru.md).

## Вставка в README

```markdown
![Как Мастер Чиф планирует](readme_gif/01_master_chief_planning.gif)
![Передача исполнителю, ревью и дашборд](readme_gif/02_delegation_review_dashboard.gif)
![Настройка проекта под новую задачу](readme_gif/03_project_setup.gif)
![LM Studio и OpenRouter](readme_gif/04_lmstudio_openrouter.gif)
![Управление дашбордом](readme_gif/05_dashboard_controls.gif)
```

## Пересборка

Нужны Python и Pillow; шрифты Segoe UI / Consolas берутся из Windows.

```powershell
cd readme_gif/source
py gif1_planning.py; py gif2_delegation.py; py gif3_setup.py; py gif4_models.py; py gif5_dashboard.py
```

`gifkit.py` — общие примитивы (карточки, стрелки, подписи шагов, сборка GIF с общей палитрой).
Текст каждого шага задаётся в списке `STEPS` соответствующего скрипта.
