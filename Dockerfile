FROM python:3.11-slim
WORKDIR /app

# バックエンド
COPY backend/ /app/backend/
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# フロントエンド静的ファイル
COPY frontend/ /app/frontend/

EXPOSE 8080
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "--chdir", "/app", "backend.app:app"]
