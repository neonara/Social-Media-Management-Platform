#!/bin/bash
set -e

echo "=== Docker Container Debug Information ==="
echo "Container hostname: $(hostname)"
echo "Container user: $(whoami)"
echo "Container working directory: $(pwd)"

# Change to the application directory
cd /app

# Debug: List contents of /app directory
echo "=== Contents of /app directory ==="
ls -la /app/

# Debug: Check if we have any Python files at all
echo "=== Looking for Python files in /app ==="
find /app -name "*.py" -type f 2>/dev/null || echo "No Python files found in /app"

# Debug: Check if manage.py exists in the root filesystem
echo "=== Looking for manage.py anywhere in the container ==="
find / -name "manage.py" -type f 2>/dev/null || echo "No manage.py found anywhere in container"

# Check if manage.py exists
if [ ! -f "/app/manage.py" ]; then
    echo "ERROR: manage.py not found in /app directory"
    echo "This suggests the Docker image was not built correctly."
    echo "Please rebuild the Docker image with: docker build -t <your-image-name> ."
    exit 1
fi

echo "Running database migrations..."
python manage.py migrate

echo "Starting Django application..."
exec "$@"
