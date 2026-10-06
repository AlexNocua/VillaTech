FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements*.txt /tmp/requirements/
RUN pip install --no-cache-dir -r /tmp/requirements/requirements-production.lock.txt
RUN useradd --uid 10001 --create-home app
COPY --chown=app:app . /app
USER app
WORKDIR /app/backend
CMD ["sh", "/app/deploy/start-railway.sh"]
