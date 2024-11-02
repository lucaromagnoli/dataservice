ARG PYTHON_VERSION=3.12-slim
FROM python:${PYTHON_VERSION}-slim

# Install system dependencies if any (e.g., build tools)
RUN apt-get clean && apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock /app/

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy the rest of the project
COPY dataservice /app/dataservice
COPY tests /app/tests
COPY noxfile.py README.rst /app/

# Install project dependencies
RUN poetry config virtualenvs.create false
RUN poetry install --with dev -E playwright --no-root

# Install Nox
RUN pip install --no-cache-dir nox nox-poetry

# Install playwright
RUN python -m playwright install --with-deps

# Default command
CMD ["nox", "--non-interactive"]
