# ---- Builder Stage ----
FROM python:3.11-slim as builder

# Install build dependencies (only curl needed for Poetry install)
RUN apt-get update && apt-get install -y curl tzdata && rm -rf /var/lib/apt/lists/*

# Set timezone (can be set early)
ENV TZ=America/Chicago
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install Poetry
ENV POETRY_HOME=/opt/poetry
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python3 - --version 1.8.3 # Pin poetry version

WORKDIR /app

# Copy only files needed for dependency installation
COPY pyproject.toml poetry.lock ./

# Install production dependencies and export requirements
# Using --only main to install only main dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main \
    && poetry export -f requirements.txt --output requirements.txt --without-hashes

# Copy the rest of the application code
COPY . .

# ---- Final Stage ----
FROM python:3.11-slim

# Install runtime system dependencies
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

# Set timezone
ENV TZ=America/Chicago
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# Copy artifacts from builder stage
COPY --from=builder /app/requirements.txt ./
COPY --from=builder /app /app

# Install runtime dependencies using pip
RUN pip install --no-cache-dir --requirement requirements.txt

# Set Python path
ENV PYTHONPATH=/app

# Add health check (kept the original, consider improving if needed)
HEALTHCHECK --interval=30s --timeout=3s \
  CMD ps aux | grep workflow.py | grep -v grep || exit 1

# Run the workflow scheduler using python directly
CMD ["python", "workflow.py"]
