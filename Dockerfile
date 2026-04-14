# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
# Note: .dockerignore excludes source data (~1.8GB) but includes
# the pre-built bible.db (~350MB) so it ships with every deploy.
COPY . .

# Inject git commit hash into service worker for automatic cache busting
ARG SW_VERSION=dev
RUN sed -i "s/__SW_VERSION__/${SW_VERSION}/g" frontend/static/sw.js

# Create non-root user for runtime
RUN adduser --disabled-password --gecos '' --home /home/appuser appuser && \
    apt-get update && apt-get install -y --no-install-recommends gosu && \
    rm -rf /var/lib/apt/lists/*

# Expose the port the app runs on
EXPOSE 8000

# Entrypoint runs as root for DB sync, then drops to appuser for uvicorn
CMD ["sh", "scripts/entrypoint.sh"]
