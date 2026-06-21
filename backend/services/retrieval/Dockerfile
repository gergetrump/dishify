FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY shared/dishify-contracts /shared/dishify-contracts
COPY shared/dishify-vector-store /shared/dishify-vector-store
RUN pip install --no-cache-dir /shared/dishify-contracts /shared/dishify-vector-store

COPY services/retrieval/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/retrieval/app ./app

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
