FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /service

COPY pyproject.toml README.md ./
COPY app/__init__.py ./app/__init__.py
RUN pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
RUN pip install .

COPY app ./app
COPY data ./data
RUN pip install --no-deps .

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
