# Desktop Roadmap — Electron + PyInstaller

План превращения Open Notebook (форк) в нативное десктоп-приложение.

**Цель:** один installer, offline-first данные на машине пользователя, UI в Electron, backend упакован через PyInstaller.

**Статус:** Фаза 2 — Electron shell (scaffold)  
**Ориентир до beta:** 4–6 недель (после успешного spike)

---

## Текущая архитектура (web)

Open Notebook — не «фронт + один API», а **четыре процесса**:

| Процесс | Порт | Роль |
|---------|------|------|
| SurrealDB | 8000 | БД, векторный поиск |
| FastAPI (API) | 5055 | REST, LangGraph, миграции |
| surreal-commands worker | — | Фоновые задачи (podcasts, embeddings) |
| Next.js standalone | 8502 | UI + proxy `/api/*` → backend |

Референс для оркестрации: `Dockerfile.single`, `supervisord.single.conf`.

---

## Целевая архитектура (desktop)

```
┌─────────────────────────────────────────────────────────┐
│  Electron Main Process                                   │
│  • lifecycle, tray, single-instance, auto-update         │
│  • spawn / monitor / graceful shutdown дочерних процессов│
│  • DATA_FOLDER → app.getPath('userData')/data            │
└────────┬────────────────────────────────────────────────┘
         │
    ┌────┴────┬──────────────┬──────────────┬─────────────┐
    ▼         ▼              ▼              ▼             │
 SurrealDB  open-notebook-  open-notebook-  Next.js       │
 (binary)   api/ (PyInstaller  worker/       (node         │
            --onedir)        --onedir)       server.js)    │
 :8000       :5055                          :8502          │
         │                                    │             │
         └────────────────────────────────────┘             │
                              ▼                              │
              BrowserWindow → http://127.0.0.1:8502 ◄────────┘
```

### Данные пользователя

Вне bundle, в user data directory (аналог `DATA_FOLDER` из [docs/1-INSTALLATION/windows-native.md](docs/1-INSTALLATION/windows-native.md)):

```
macOS:   ~/Library/Application Support/Open Notebook/data/
Windows: %APPDATA%/Open Notebook/data/
Linux:   ~/.config/open-notebook/data/

├── surrealdb/       # rocksdb files
├── uploads/
├── sqlite-db/       # LangGraph checkpoints
└── tiktoken-cache/
```

### Переменные окружения (desktop)

```env
SURREAL_URL=ws://127.0.0.1:8000/rpc
SURREAL_USER=root
SURREAL_PASSWORD=<generated>
INTERNAL_API_URL=http://127.0.0.1:5055
API_URL=                      # пусто → relative /api через Next.js rewrites
DATA_FOLDER=<userData>/data
API_RELOAD=false
API_HOST=127.0.0.1
OPEN_NOTEBOOK_ENCRYPTION_KEY=<generated on first run>
```

---

## Ключевые технические решения

| Решение | Выбор | Обоснование |
|---------|-------|-------------|
| UI shell | **Electron** | BrowserWindow на localhost; минимальные изменения фронта |
| Frontend | **Next.js standalone** (как сейчас) | Уже `output: "standalone"`; rewrites, `/config`, SSE-proxy |
| Backend packaging | **PyInstaller `--onedir`** | Два bundle: API + worker; проще LangChain/LangGraph, чем Nuitka |
| БД | **SurrealDB binary** (v2) | Не упаковывается PyInstaller; отдельный бинарник per OS/arch |
| ffmpeg | **imageio-ffmpeg** wheel | Уже в зависимостях; нужен для подкастов |
| Node.js | **Bundled** (Electron extraResources или embedded) | Next.js standalone требует `node server.js` |
| Формат дистрибутива | **`--onedir`, не `--onefile`** | Быстрый старт, меньше проблем с numpy/ffmpeg/migrations |

---

## Структура каталогов (новое)

```
desktop/
├── main.ts                 # Electron main process
├── preload.ts              # безопасный bridge (если понадобится)
├── process-manager.ts      # spawn / health / shutdown
├── paths.ts                # resource paths (dev vs prod)
├── entry_api.py            # PyInstaller entry: uvicorn
├── entry_worker.py         # PyInstaller entry: surreal-commands worker
├── open-notebook-api.spec  # PyInstaller spec (API)
├── open-notebook-worker.spec
├── electron-builder.yml    # или конфиг в package.json
└── package.json

resources/                  # артеfact сборки (gitignore)
├── surrealdb/
├── api/
├── worker/
└── frontend/
```

---

## Фазы реализации

### Фаза 0 — Spike PyInstaller (3–5 дней)

**Цель:** доказать, что API собирается и работает без Docker.

- [x] `desktop/entry_api.py` — uvicorn без reload
- [x] Черновик `open-notebook-api.spec`:
  - `datas`: migrations, ai/assets, tiktoken cache, jinja templates, `pyproject.toml`
  - `hiddenimports`: uvicorn, fastapi, langchain*, langgraph*, surrealdb, commands
- [x] `open_notebook/utils/frozen.py` — `resource_path`, `migration_path`
- [x] `DATA_FOLDER` из env в `open_notebook/config.py`
- [x] `desktop/build_api.sh`, `desktop/smoke_test.py`, `desktop/README.md`
- [x] Локально: SurrealDB v2 + собранный API
- [x] Smoke-тесты (базовые):
  - [x] `GET /api/config`
  - [x] CRUD notebook
  - [ ] Upload PDF + embedding
  - [ ] Chat (SSE)
- [x] **Go/No-Go:** PyInstaller для API — **GO** (продолжаем desktop roadmap)

### Фаза 1 — Worker + path fixes (1 неделя)

- [x] `desktop/entry_worker.py` + `open-notebook-worker.spec`
- [x] `desktop/runtime_bootstrap.py` (общий bootstrap для API/worker)
- [x] `desktop/build_worker.sh`, `build_all.sh`, `smoke_worker.py`
- [x] `resource_path()` helper для frozen mode (`open_notebook/utils/frozen.py`)
- [x] `DATA_FOLDER` из env в `open_notebook/config.py`
- [x] Версия приложения: `importlib.metadata` + bundled `pyproject.toml`
- [x] `API_RELOAD=false` / worker `--import-modules commands` в entry points
- [x] `connection_tester.py` — assets через `resource_path()` (frozen-safe)
- [x] `smoke_worker.py` — регистрация `commands` при старте
- [ ] Worker smoke: `process_source` / podcast job end-to-end (нужен AI provider)

### Фаза 2 — Electron shell (1–2 недели)

- [x] `desktop/electron/` scaffold (Electron + TypeScript + electron-builder)
- [x] Process manager:
  - [x] Порядок старта: SurrealDB → API → worker → Next.js
  - [x] Health check API перед открытием окна
  - [x] Graceful shutdown (SIGTERM всем детям)
  - [x] Single-instance lock
- [x] `BrowserWindow` → `http://127.0.0.1:3000` (dev) / `:8502` (standalone)
- [x] Splash / «Starting services…»
- [x] Генерация `OPEN_NOTEBOOK_ENCRYPTION_KEY` и SurrealDB credentials на first run
- [x] Логи: `%userData%/logs/` (api, worker, surrealdb, frontend)
- [ ] E2E: полный запуск через Electron на macOS (без Docker, с bundled SurrealDB — Фаза 4)

### Фаза 3 — Frontend bundle (3–5 дней)

- [ ] `npm run build` → копировать `.next/standalone` в `resources/frontend/`
- [ ] Spawn: `node server.js` с `PORT=8502`, `HOSTNAME=127.0.0.1`
- [ ] Проверить file upload до 100 MB (`proxyClientMaxBodySize` в `next.config.ts`)
- [ ] Проверить SSE routes: `/api/search/ask`, source chat messages

### Фаза 4 — Бинарные зависимости + packaging (1 неделя)

- [ ] SurrealDB v2: download per platform (macOS arm64/x64, Windows x64, Linux x64)
- [ ] ffmpeg через `imageio-ffmpeg` в worker/api spec
- [ ] electron-builder: `extraResources` для api/, worker/, surrealdb/, frontend/
- [ ] Иконки приложения (`.icns`, `.ico`)
- [ ] Оценка размера installer (ориентир: 600 MB – 1 GB)

### Фаза 5 — UX и production (1–2 недели)

- [ ] First-run: encryption key, подсказка по AI credentials (Settings UI уже есть)
- [ ] Меню: Open Data Folder, Open Logs, Quit
- [ ] System tray (опционально)
- [ ] Auto-update: `electron-updater` + GitHub Releases
- [ ] Code signing: Apple notarization, Windows Authenticode
- [ ] Deep links (опционально): `open-notebook://notebook/{id}`

### Фаза 6 — CI/CD (1 неделя)

- [ ] GitHub Actions matrix: `macos-arm64`, `macos-x64`, `windows-x64`, `linux-x64`
- [ ] Pipeline:
  1. Build frontend (standalone)
  2. PyInstaller api + worker
  3. Download surrealdb for target
  4. electron-builder
  5. Headless smoke: launch → curl `/api/config`
- [ ] Release artifacts на GitHub Releases

---

## PyInstaller — чеклист spec

### Data files (`datas`)

| Путь | Назначение |
|------|------------|
| `open_notebook/database/migrations/*.surrealql` | миграции при старте API |
| `open_notebook/ai/assets/*` | connection test audio |
| tiktoken cache (`o200k_base`, …) | offline tokenization |
| Jinja templates (ai-prompter, podcast-creator) | prompts |
| `pyproject.toml` | версия в `/api/config` |

### Hidden imports (стартовый список, дополнять итеративно)

```
uvicorn, uvicorn.logging, uvicorn.loops.auto
uvicorn.protocols.http.auto, uvicorn.lifespan.on
fastapi, starlette, pydantic, pydantic_core
langchain, langchain_core, langchain_community
langchain_openai, langchain_anthropic, langchain_ollama, ...
langgraph, langgraph_checkpoint_sqlite
surrealdb, surreal_commands
esperanto, content_core, ai_prompter, podcast_creator
tiktoken, tiktoken_ext, numpy, httpx, loguru
commands, commands.podcast_commands, commands.source_commands,
commands.embedding_commands, commands.source_commands
api, api.main
open_notebook, open_notebook.graphs.*
```

### Команды сборки (черновик)

```bash
# API
pyinstaller --clean desktop/open-notebook-api.spec

# Worker
pyinstaller --clean desktop/open-notebook-worker.spec
```

---

## Изменения в существующем коде (минимальные)

| Файл | Изменение |
|------|-----------|
| `open_notebook/config.py` | `DATA_FOLDER` из env |
| `open_notebook/database/async_migrate.py` | пути к migrations через `resource_path()` |
| `api/routers/config.py` | версия без хрупкого `Path(__file__).parent.../pyproject.toml` |
| `run_api.py` | без изменений для web; desktop использует `entry_api.py` |
| `frontend/next.config.ts` | без изменений |
| `frontend/src/lib/config.ts` | без изменений (relative API URL уже default) |
| `.gitignore` | `desktop/resources/`, `dist/`, `build/` |

---

## Риски

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Hidden imports LangChain/LangGraph | Высокая | Итеративный spec + CI smoke |
| Большой размер installer (600 MB–1 GB) | Высокая | `--onedir`, delta updates |
| Windows Defender false positives | Средняя | Code signing |
| Worker не находит `commands` | Средняя | explicit hiddenimports + тест job |
| Порт занят | Средняя | dynamic ports или retry с другим портом |
| `pyproject.toml` / migrations paths в frozen mode | Средняя | `resource_path()` + datas в spec |
| macOS / Windows ARM64 | Средняя | отдельные SurrealDB + CI matrix |

---

## Критерии готовности beta

- [ ] Установка одним installer без Docker и без установленного Python
- [ ] First run → создание data dir → UI открывается без ручной настройки
- [ ] Notebook, upload PDF, chat, search, podcast generation работают
- [ ] Quit корректно останавливает все 4 процесса
- [ ] Данные сохраняются между перезапусками
- [ ] macOS + Windows builds в CI

---

## Открытые вопросы

1. **Платформы v1:** только macOS, или macOS + Windows + Linux?
2. **MVP fallback:** допустим ли bundled `.venv` на время, пока PyInstaller spec стабилизируется?
3. **Offline AI:** bundled Ollama в installer или только cloud/local через Settings?
4. **Имя приложения и bundle id:** `Open Notebook` / `ai.open-notebook.desktop`?

---

## Альтернативы (не в scope v1)

| Подход | Когда рассмотреть |
|--------|-------------------|
| Bundled `.venv` без PyInstaller | Быстрый MVP (3–5 дней) |
| Nuitka | После stable desktop, если нужен меньший footprint |
| Tauri | Если критичен размер RAM |
| Docker Desktop wrapper | Не native desktop |

---

## Ссылки

- [Architecture](docs/7-DEVELOPMENT/architecture.md)
- [Windows native install](docs/1-INSTALLATION/windows-native.md) — 4 процесса, `DATA_FOLDER`
- [Single container (deprecated)](docs/1-INSTALLATION/single-container.md) — blueprint оркестрации
- [Development setup](docs/7-DEVELOPMENT/development-setup.md)

---

*Создано: 2026-06-29*
