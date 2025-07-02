FROM python:3.12-slim

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=planit.settings
ENV PORT=8000

# Create the app directory
RUN mkdir /app
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  libpq-dev \
  libpq5 \
  netcat-openbsd \
  postgresql-client \
  && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements file and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Copy entrypoint script
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Set entrypoint to run migrations before starting the app
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Use Daphne for ASGI applications (WebSocket support)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "planit.asgi:application"]
