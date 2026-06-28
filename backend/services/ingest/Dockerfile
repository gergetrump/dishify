FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ffmpeg transcodes browser audio (webm/opus) into a Gemini-supported format.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY shared/dishify-contracts /shared/dishify-contracts
RUN pip install --no-cache-dir /shared/dishify-contracts

COPY services/ingest/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/ingest/app ./app

EXPOSE 8005

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]
