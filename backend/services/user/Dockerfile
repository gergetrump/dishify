FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY shared/dishify-contracts /shared/dishify-contracts
RUN pip install --no-cache-dir /shared/dishify-contracts

COPY services/user/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/user/app ./app

EXPOSE 8004

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
