# Быстрый старт (RU): кит для OpenCode на примере Java / Spring Boot

> Инструкция «с нуля»: как подключить кит к своему проекту и начать работать в OpenCode.
> English version: [QUICKSTART.en.md](QUICKSTART.en.md)

---

## 1. Что это такое

Этот кит превращает OpenCode в схему **«мозг + исполнители»**:

- 🧠 **Мозг** (`build`, облачная модель) — планирует задачу, пишет **каркас кода с техническим заданием (ТЗ)**, сразу пишет **тесты**, проверяет результат.
- 🛠 **Исполнитель** (`executor`, локальная модель в LM Studio) — заполняет **только тела методов** строго по ТЗ. Ничего лишнего не трогает.

Цикл работы всегда такой:

```
ты:   /module task
мозг: каркас + ТЗ + тесты (тесты пока красные — это нормально)
      └─ передаёт исполнителю по одному методу
исполнитель: заполняет тело по ТЗ
мозг: гоняет тесты → зелёные → модуль готов
```

Пример ниже — проект на **Java (Spring Boot)**. Схема одинаковa для любого языка: меняются только команды тестов.

---

## 2. Что нужно установить

| Что | Зачем | Проверка |
| --- | --- | --- |
| OpenCode | сам агент | — |
| LM Studio | локальная модель-исполнитель | `py kit/check_env.py` |
| Python 3.13 | **только** утилиты кита | `py --version` |
| JDK 21 | компилировать Java | `java -version` |
| Maven | сборка и тесты Java | `mvn -v` |

> Python нужен киту (поиск Obsidian и проверки), а не твоему Java-проекту.

В LM Studio нужно **загрузить модель** (кнопка **Load**) и включить сервер: **Developer → Start Server**.

---

## 3. Шаг 1. Создать Java-проект

1. Открой [start.spring.io](https://start.spring.io)
2. Заполни:
   - **Project:** Maven
   - **Language:** Java
   - **Spring Boot:** последняя стабильная 3.x
   - **Java:** 21
   - **Dependencies:** `Spring Web`, `Validation`
3. Нажми **Generate** → скачается zip.
4. Распакуй его, например в `D:\PROJECTS\task-api`.

Получится примерно так:

```
task-api/
├── pom.xml
└── src/
    ├── main/java/com/example/taskapi/
    └── test/java/com/example/taskapi/
```

---

## 4. Шаг 2. Положить кит в проект

Скопируй в корень `task-api/` четыре вещи:

```
opencode.jsonc        ← агенты и модели
AGENTS.md             ← правила работы
kit/                  ← утилиты (поиск Obsidian, проверка среды)
.opencode/            ← команды /plan-project и /module
```

Итого в корне проекта должно быть:

```
task-api/
├── opencode.jsonc
├── AGENTS.md
├── kit/
├── .opencode/
├── pom.xml
└── src/
```

---

## 5. Шаг 3. Настроить `AGENTS.md` под Java

Открой `AGENTS.md` и отредактируй **две секции** с пометкой `# EDIT`.

**Секция `Project stack`:**

```md
## Project stack  # EDIT: language, build tool, test command
- Language: Java 21 (`java -version`). Build tool: Maven (`mvn`).
- Tests: JUnit 5. Run: `mvn -q test`.
- Compile only: `mvn -q compile`.
- Run the app: `mvn spring-boot:run`.
```

**Секция `Project layout`:**

```md
## Project layout  # EDIT: folders and files of this project
- `src/main/java/com/example/taskapi/` — application code.
- `src/test/java/com/example/taskapi/` — tests.
- `pom.xml` — Maven build file.
```

> Всё остальное в `AGENTS.md` менять не нужно. Команды `/module` и `/plan-project` уже языко-независимы.

---

## 6. Шаг 4. Проверить среду

Открой терминал в папке проекта и выполни:

```powershell
py kit/check_env.py
```

Ожидаемо: `Result: ready for use`.

Если красное — смотри раздел **10. Частые проблемы**.

---

## 7. Шаг 5. Запустить OpenCode

Открой OpenCode **в папке `task-api`** (там, где лежит `opencode.jsonc`).

Проверь, что всё видно:
- набери `/` — должны быть команды `/plan-project` и `/module`;
- спроси: «Прочитай план работ» — мозг найдёт Obsidian через `kit/find_vault.py` (или возьмёт `currentsteps.md`).

---

## 8. Шаг 6. Спланировать проект

Напиши в чат OpenCode:

```text
/plan-project REST API задач на Spring Boot: model, service, controller
```

Мозг **только составит план** (разобьёт на модули и запишет чеклист) — код не пишет.

Пример результата:

```md
## Modules
- [ ] model      — Task + хранилище
- [ ] service    — list / create / complete / delete
- [ ] controller — REST-ручки
```

Проверь план и напиши «ок, поехали».

---

## 9. Шаг 7. Делать модуль за модулем

Для каждого модуля из плана:

```text
/module model
```

Что произойдёт автоматически:

1. Мозг создаст **каркас** `Task.java` с Javadoc-ТЗ и заглушкой:
   ```java
   public Task create(String title) {
       throw new UnsupportedOperationException("TODO: executor");
   }
   ```
2. Мозг создаст **тесты** `TaskServiceTest.java` и запустит `mvn -q test` — тесты **красные** (так надо).
3. Мозг вызовет **исполнителя** заполнить тело метода по ТЗ.
4. Исполнитель заполнит **только тело**.
5. Мозг снова запустит `mvn -q test` → **зелёные** → модуль готов, идём к следующему.

Повтори:

```text
/module service
/module controller
```

> Правило: **одному исполнителю — один кусок**. Не проси «сделай весь проект сразу».

---

## 10. Шаг 8. Проверить и запустить

```powershell
mvn -q test             # тесты
mvn spring-boot:run     # запустить приложение
```

В другом окне:

```powershell
curl http://localhost:8080/tasks
```

---

## 11. Частые проблемы

| Симптом | Причина | Что делать |
| --- | --- | --- |
| `Result: test failed` в `check_env` | LM Studio не запущен / модель не загружена | Developer → Start Server; нажать Load у модели |
| Команд `/module` не видно | `.opencode/` не скопирован или OpenCode открыт не в корне проекта | Проверь папку проекта |
| `mvn` не найден | Maven не установлен / не в PATH | Установи Maven, перезапусти терминал |
| Тесты не компилируются | Исполнитель забыл импорт | Скажи мозгу: «проверь и почини, это ревью» |
| Мозг всё делает сам | Не читает `AGENTS.md` | Проверь, что `AGENTS.md` в корне проекта |
| `currentsteps.md` не создаётся | Obsidian не найден | Это нормально: план будет в проекте |

---

## 12. Что дальше

- `README.md` — обзор проекта.
- В Obsidian (база знаний «Мультиагенты. Opencode»): подробные учебники, разборы кода и полный Java-кейс.

---

> Коротко: **положи кит в проект → поправь две секции в `AGENTS.md` → `/plan-project` → `/module` по очереди → тесты зелёные.**
