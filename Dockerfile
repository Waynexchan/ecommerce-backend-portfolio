# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory to /app
WORKDIR /app

# Copy all files from current directory to /app in container
COPY . .

# Install required packages
RUN apt-get update && apt-get install -y build-essential libpq-dev

# Create a virtual environment
RUN python -m venv /opt/venv

# Set the PATH environment variable
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install required Python packages
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Create directories for static and media files
RUN mkdir -p /app/staticfiles /app/media /app/logs /app/logs/django

# Define build arguments
ARG EMAIL_HOST_USER
ARG EMAIL_HOST_PASSWORD
ARG STRIPE_PUBLIC_KEY
ARG STRIPE_SECRET_KEY
ARG PAYPAL_CLIENT_ID
ARG PAYPAL_SECRET_ID
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG AWS_STORAGE_BUCKET_NAME
ARG AWS_S3_REGION_NAME
ARG DATABASE_URL
ARG NAME
ARG USER
ARG PASSWORD
ARG HOST
ARG PORT
ARG USE_S3

# Set environment variables from build arguments
ENV EMAIL_HOST_USER=${EMAIL_HOST_USER}
ENV EMAIL_HOST_PASSWORD=${EMAIL_HOST_PASSWORD}
ENV STRIPE_PUBLIC_KEY=${STRIPE_PUBLIC_KEY}
ENV STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
ENV PAYPAL_CLIENT_ID=${PAYPAL_CLIENT_ID}
ENV PAYPAL_SECRET_ID=${PAYPAL_SECRET_ID}
ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ENV AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
ENV AWS_STORAGE_BUCKET_NAME=${AWS_STORAGE_BUCKET_NAME}
ENV AWS_S3_REGION_NAME=${AWS_S3_REGION_NAME}
ENV DATABASE_URL=${DATABASE_URL}
ENV NAME=${NAME}
ENV USER=${USER}
ENV PASSWORD=${PASSWORD}
ENV HOST=${HOST}
ENV PORT=${PORT}
ENV USE_S3=${USE_S3}

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port 8000
EXPOSE 8000

# Start Gunicorn and use the PORT environment variable
CMD exec gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 3
