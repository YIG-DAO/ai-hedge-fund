FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    jq \
    tzdata \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set timezone
ENV TZ=America/Chicago
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy Poetry files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Install the project
RUN poetry install --no-interaction --no-ansi

# Set Python path
ENV PYTHONPATH=/app

# Add health check
HEALTHCHECK --interval=30s --timeout=3s \
  CMD ps aux | grep workflow.py | grep -v grep || exit 1

# Run the workflow scheduler
CMD ["poetry", "run", "python", "workflow.py"]
