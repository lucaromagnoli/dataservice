ARG PYTHON_VERSION=3.12-slim
FROM python:${PYTHON_VERSION}-slim

# Install system dependencies if any (e.g., build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock /app/

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy the rest of the project
COPY . /app

# Install project dependencies
RUN poetry config virtualenvs.create false
RUN poetry install --no-root

# Install Nox
RUN pip install --no-cache-dir nox nox-poetry


# Default command
CMD ["nox", "--non-interactive"]
