# offline-news

A terminal-driven RSS pipeline that fetches, parses, normalises, and enriches news articles into a local database. Runs on Django + Celery + Redis + Postgres.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python package manager)

Install `uv` if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Setup

### 1. Install dependencies

```bash
uv sync
```

This creates a `.venv` and installs all packages. It also generates `uv.lock`, which is required for Docker builds.

### 2. Configure environment

Copy the example env file:

```bash
cp .env.example .env
```

The defaults work out of the box for local Docker development. Change `SECRET_KEY` if needed.

### 3. Generate migrations

```bash
source .venv/bin/activate
python manage.py makemigrations
```

### 4. Start all services

```bash
docker compose up --build -d
```

This starts:
| Service | Role |
|---------|------|
| `db` | Postgres 16 |
| `redis` | Celery broker and result backend |
| `web` | Django (Gunicorn) on port 8000 |
| `worker` | Celery worker (runs pipeline tasks) |
| `beat` | Celery Beat (schedules periodic tasks) |

Migrations run automatically on startup via `entrypoint.sh`.

### 5. Create a superuser

```bash
docker compose exec web python manage.py createsuperuser
```

## Pulling RSS feeds

### 1. Add a source

Open Django Admin at `http://localhost:8000/admin`, go to **Feeds > Sources > Add Source** and fill in:

| Field | Example |
|-------|---------|
| Name | `BBC News` |
| Slug | `bbc-news` |
| RSS URL | `https://feeds.bbci.co.uk/news/rss.xml` |
| Is active | checked |
| Fetch interval | `60` (minutes) |

Save. Add as many sources as you like.

### 2. Schedule automatic fetching

Go to **Periodic Tasks > Add Periodic Task**:

- **Name**: `Fetch all feeds` (any label)
- **Task**: `feeds.tasks.fetch_all_active_feeds`
- **Interval schedule**: create one — e.g. every `60` minutes

Save. Celery Beat will now trigger the pipeline on that interval.

### 3. Trigger a fetch immediately

Don't want to wait for the schedule? Run it now:

```bash
docker compose exec web python manage.py shell -c "from feeds.tasks import fetch_all_active_feeds; fetch_all_active_feeds.delay()"
```

### 4. Check the results

Watch the worker processing articles in real time:

```bash
docker compose logs -f worker
```

Or inspect stored articles and fetch history in the admin under **Articles** and **Feeds > Fetch Logs**.

## Viewing logs

```bash
docker compose logs -f worker   # pipeline task output
docker compose logs -f beat     # scheduler output
```

## Stopping

```bash
docker compose down             # stop services, keep data
docker compose down -v          # stop services and delete all data
```

## Project structure

```
offline_news/       # Django project settings, celery config
feeds/              # Source and FetchLog models, pipeline tasks
  pipeline/
    fetcher.py      # Downloads RSS XML
    parser.py       # Parses RSS/Atom into raw dicts
    normalizer.py   # Canonicalises URLs, strips tracking params
    enricher.py     # Fetches full article body via trafilatura
articles/           # Article model
```
