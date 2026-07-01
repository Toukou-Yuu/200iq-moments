FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY data ./data

RUN pip install --no-cache-dir .

EXPOSE 8000 8201

CMD ["200iq-moments", "serve", "--host", "0.0.0.0", "--port", "8000"]
