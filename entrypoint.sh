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

# Create static directories if they don't exist
echo "Creating static directories..."
mkdir -p /app/static
mkdir -p /app/staticfiles
mkdir -p /app/media

echo "Running database migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create default superuser if necessary (optional)
echo "Creating superuser (if necessary)..."
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@planit.com').exists():
    user = User.objects.create_superuser('admin@planit.com', 'admin123')
    user.is_superadministrator = True
    user.save()
    print('Superuser created: admin@planit.com / admin123')
else:
    print('Superuser already exists')
END

echo "Starting Django application..."
exec "$@"
