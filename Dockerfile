# Dockerfile

FROM python:3.7-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt && rm -rf /root/.cache

COPY src .
CMD ["python", "-u", "/app/estate_feeder.py"]