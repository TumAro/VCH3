FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install dependencies first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and dataset
COPY data/ data/
COPY src/ src/
COPY run.py .

EXPOSE 8000

# Launch web server headless; host and port adapt to $HOST and $PORT
CMD ["python", "run.py", "--host", "0.0.0.0", "--no-browser"]
