FROM python:3.12-slim

WORKDIR /code

RUN pip install uv
COPY pyproject.toml .
RUN uv pip install --system -e .

COPY . .
