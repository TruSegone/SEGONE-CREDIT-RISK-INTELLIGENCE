FROM python:3.12-slim

WORKDIR /app

ENV SEGONE_PROJECT_ROOT=/app \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Train a reproducible synthetic model into the image so each fresh instance
# starts with the same checked-in training workflow and has no volume dependency.
RUN python -m app.ml.train

EXPOSE 10000

# Render provides PORT at runtime; local Docker runs fall back to port 8000.
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
