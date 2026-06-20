FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY shared/dishify-contracts /shared/dishify-contracts
COPY shared/dishify-ranking /shared/dishify-ranking
RUN pip install --no-cache-dir /shared/dishify-contracts /shared/dishify-ranking

COPY services/recommendation/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/recommendation/app ./app

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
