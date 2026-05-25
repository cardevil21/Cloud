# Official Python image use করব
FROM python:3.11-slim

# Working directory set
WORKDIR /app

# Dependencies install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App copy
COPY app.py .

# Port expose
EXPOSE 5000

# Gunicorn দিয়ে run (production-ready)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "2", "--timeout", "120", "app:app"]
