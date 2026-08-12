web: python -c "from database import init_db; init_db()" && gunicorn app:app --workers 1 --threads 8 --timeout 60
