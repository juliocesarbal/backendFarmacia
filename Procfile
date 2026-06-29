web: python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --workers 1 --threads 4 --max-requests 5 --max-requests-jitter 2 --log-file -
