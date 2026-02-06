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

# Expose the port the app runs on
EXPOSE 8000

# Entrypoint syncs the DB from image to persistent volume, then starts uvicorn
CMD ["sh", "scripts/entrypoint.sh"]
