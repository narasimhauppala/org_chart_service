# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# Install postgresql-client for pg_isready command used in entrypoint.sh
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Copy only requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run the application
# We will override this in docker-compose to include running migrations
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 