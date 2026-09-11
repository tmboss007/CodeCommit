FROM python:3.11-slim
WORKDIR /app
COPY requirements-simple.txt .
RUN pip install --no-cache-dir -r requirements-simple.txt
COPY . .
ENV DATABASE_URL=sqlite:///./nexus_r.db
ENV CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
