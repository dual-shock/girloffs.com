FROM python:3.13.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/backend
COPY backend/requirements.txt .
# --only-binary: install prebuilt wheels only, so no package can run its own build script here
RUN pip install --no-cache-dir pip==26.2.2 && pip install --no-cache-dir --only-binary=:all: -r requirements.txt

COPY backend/app ./app
COPY frontend /srv/frontend

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
