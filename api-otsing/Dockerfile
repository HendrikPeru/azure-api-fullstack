FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir flask flask-cors azure-storage-blob

CMD ["python", "app.py"]