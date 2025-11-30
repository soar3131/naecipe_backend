FROM python:3.11-slim

WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY src/ ./src/

# Install the application
RUN poetry install --no-interaction --no-ansi

EXPOSE 8003

CMD ["uvicorn", "cookbook_service.main:app", "--host", "0.0.0.0", "--port", "8003"]
