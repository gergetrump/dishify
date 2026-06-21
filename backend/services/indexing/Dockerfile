FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY shared/dishify-contracts /shared/dishify-contracts
COPY shared/dishify-vector-store /shared/dishify-vector-store
RUN pip install --no-cache-dir /shared/dishify-contracts /shared/dishify-vector-store

COPY services/indexing/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/indexing/app ./app

ENTRYPOINT ["python", "-m", "app.main"]
