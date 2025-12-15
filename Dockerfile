FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

RUN apt-get update && apt-get install -y curl

WORKDIR /app

# Copier les fichiers de dépendances
COPY pyproject.toml ./
COPY README.md ./

# Copier le code de l'application
COPY . .

# Installer les dépendances avec uv
RUN uv lock && uv sync --frozen --no-cache
RUN uv add psycopg2-binary && uv sync

# Créer un utilisateur non-root
#RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
#USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
