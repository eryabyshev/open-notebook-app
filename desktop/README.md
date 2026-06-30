# Desktop — Phase 0: PyInstaller API Spike

Сборка standalone API bundle для будущего Electron-приложения.

## Быстрый старт

### 1. Зависимости

```bash
uv sync --group desktop
```

### 2. SurrealDB (обязательно **v2**)

Open Notebook мигрирует схему под **SurrealDB v2** (как в `docker-compose.yml`).  
Если поставить через Homebrew, часто ставится **v3** — миграции упадут с:

`Parse error: FLEXIBLE must be specified after TYPE`

**Рекомендуется Docker (v2):**

```bash
mkdir -p data/surrealdb

docker run -d --name surrealdb -p 8000:8000 \
  -v "$(pwd)/data/surrealdb:/mydata" \
  surrealdb/surrealdb:v2 \
  start --log info --user root --pass root rocksdb:/mydata/mydatabase.db
```

Если раньше запускали SurrealDB v3 на `./data/surrealdb`, удалите каталог и создайте заново:

```bash
docker stop surrealdb 2>/dev/null; docker rm surrealdb 2>/dev/null
rm -rf data/surrealdb && mkdir -p data/surrealdb
# затем docker run ... как выше
```

Native CLI (только если это **v2**, не latest brew):

```bash
surreal version   # должно быть 2.x
surreal start --user root --pass root --bind 127.0.0.1:8000 rocksdb:./data/surrealdb
```

Создайте `.env` из примера (один раз):

```bash
cp .env.example .env
# для локального SurrealDB в .env должно быть:
# SURREAL_URL=ws://127.0.0.1:8000/rpc
```

Минимум в `.env`:

```env
SURREAL_URL=ws://127.0.0.1:8000/rpc
SURREAL_USER=root
SURREAL_PASSWORD=root
OPEN_NOTEBOOK_ENCRYPTION_KEY=dev-secret-key-change-me
```

### 3. Сборка

```bash
chmod +x desktop/build_api.sh   # один раз, если «permission denied»
./desktop/build_api.sh
# или без chmod:
bash desktop/build_api.sh
```

Артеfact: `desktop/dist/open-notebook-api/open-notebook-api`

### 4. Запуск собранного API

```bash
uv run --env-file .env desktop/dist/open-notebook-api/open-notebook-api
```

### 5. Smoke test

```bash
uv run python desktop/smoke_test.py
```

## Dev без PyInstaller

```bash
uv run --env-file .env python desktop/entry_api.py
```

## Структура

| Файл | Назначение |
|------|------------|
| `entry_api.py` | Entry point для uvicorn (dev + frozen) |
| `open-notebook-api.spec` | PyInstaller spec (`--onedir`) |
| `build_api.sh` | Сборка + pre-download tiktoken |
| `smoke_test.py` | HTTP smoke tests |

## Если сборка падает на import

Добавьте модуль в `hiddenimports` в `open-notebook-api.spec` и пересоберите:

```bash
./desktop/build_api.sh
```

## Следующий шаг (Phase 1)

Worker spec: `entry_worker.py` + `open-notebook-worker.spec`
