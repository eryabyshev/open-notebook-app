# Desktop — PyInstaller bundles (API + Worker)

Сборка standalone Python bundles для будущего Electron-приложения.

## Быстрый старт

### 1. Зависимости

```bash
uv sync --group desktop
```

### 2. SurrealDB (обязательно **v2**)

Open Notebook мигрирует схему под **SurrealDB v2** (как в `docker-compose.yml`).  
Homebrew часто ставит **v3** — миграции упадут с `FLEXIBLE must be specified after TYPE`.

**Docker (рекомендуется):**

```bash
mkdir -p data/surrealdb

docker run -d --name surrealdb -p 8000:8000 \
  -v "$(pwd)/data/surrealdb:/mydata" \
  surrealdb/surrealdb:v2 \
  start --log info --user root --pass root rocksdb:/mydata/mydatabase.db
```

`.env` (минимум):

```env
SURREAL_URL=ws://127.0.0.1:8000/rpc
SURREAL_USER=root
SURREAL_PASSWORD=root
OPEN_NOTEBOOK_ENCRYPTION_KEY=dev-secret-key-change-me
```

### 3. Сборка

```bash
# API only
bash desktop/build_api.sh

# Worker only
bash desktop/build_worker.sh

# Оба bundle
bash desktop/build_all.sh
```

Артефакты:

- `desktop/dist/open-notebook-api/open-notebook-api`
- `desktop/dist/open-notebook-worker/open-notebook-worker`

### 4. Запуск (3 процесса для полного функционала)

**Терминал 1** — SurrealDB (Docker v2)

**Терминал 2** — API:

```bash
uv run --env-file .env desktop/dist/open-notebook-api/open-notebook-api
```

**Терминал 3** — Worker (фоновые задачи: embeddings, source processing, podcasts):

```bash
uv run --env-file .env desktop/dist/open-notebook-worker/open-notebook-worker
```

**Терминал 4 (опционально)** — UI:

```bash
cd frontend && npm run dev
# http://127.0.0.1:3000
```

### 5. Smoke tests

```bash
uv run python desktop/smoke_test.py
uv run python desktop/smoke_worker.py
```

Dev без PyInstaller:

```bash
uv run --env-file .env python desktop/entry_api.py
uv run --env-file .env python desktop/entry_worker.py
```

## Структура

| Файл | Назначение |
|------|------------|
| `runtime_bootstrap.py` | cwd / sys.path для dev и frozen |
| `entry_api.py` | uvicorn entry point |
| `entry_worker.py` | surreal-commands worker entry point |
| `open-notebook-api.spec` | PyInstaller spec API |
| `open-notebook-worker.spec` | PyInstaller spec worker |
| `build_api.sh` / `build_worker.sh` / `build_all.sh` | Сборка |
| `smoke_test.py` / `smoke_worker.py` | Smoke tests |

## Если сборка падает на import

Добавьте модуль в `hiddenimports` в соответствующий `.spec` и пересоберите.

## Следующий шаг (Phase 2)

Electron shell — оркестрация SurrealDB + API + worker + Next.js в одном окне.
