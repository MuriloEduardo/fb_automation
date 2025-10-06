#!/bin/bash

# Wait for database to be ready (only for web service)
if [ "$1" = "python" ] && [ "$2" = "manage.py" ] && [ "$3" = "runserver" ]; then
    echo "Waiting for database..."
    while ! pg_isready -h db -p 5432 -U postgres; do
        echo "Database is unavailable - sleeping"
        sleep 1
    done
    echo "Database is up - executing migrations"

    # Run migrations
    echo "Running migrations..."
    python manage.py migrate

    # Create superuser if it doesn't exist
    echo "Checking for superuser..."
    python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"

    echo "Starting Django server..."
fi

# Execute the command passed to the container
exec "$@"