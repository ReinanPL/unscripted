FROM python:3.11-slim

WORKDIR /app

# Cache do Hugging Face fica em volume montado (docker-compose) para
# sobreviver a rebuilds e ao primeiro download do modelo de embedding.
ENV HF_HOME=/cache/hf

COPY pyproject.toml .

RUN pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir -e .

COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

EXPOSE 8000

CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
