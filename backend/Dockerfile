FROM python:3.14-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_NO_INTERACTION=1 \
    PYTHONPATH=/app/src

WORKDIR /app


# 解析ライブラリの native 依存：
#   libmagic1   … python-magic(libmagic) の実行時依存（種別判定）
#   build-essential … ssdeep のソースビルド用コンパイラ（python:slim には無い）
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# poetry はビルド時のみ使用
RUN pip install poetry

# 依存だけ先に入れる（レイヤキャッシュが効く：pyproject/lock が変わらない限り再利用）
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-root

# アプリ本体（src / config.toml / alembic など）
COPY . .

# 起動コマンドは compose 側で指定：
#   api        : uvicorn fsas.api.app:app --host 0.0.0.0 --port 8000
#   dispatcher : python -m fsas.dispatcher.entry