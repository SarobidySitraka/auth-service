FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Copier les fichiers de dépendances
COPY pyproject.toml ./
COPY README.md ./

# Copier le code de l'application
COPY ./app ./app

# Installer les dépendances avec uv
RUN uv lock && uv sync --frozen --no-cache
#RUN uv pip install --system --no-cache -r pyproject.toml

# Créer un utilisateur non-root
#RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
#USER appuser

EXPOSE 8000
# Health check natif Docker (compatible avec urllib.request)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1


CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]