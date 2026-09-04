# Copy this file to config/local.env.ps1, replace every placeholder, and keep
# the local file private. scripts/start.ps1 loads it automatically.
$env:STRESS_DB_HOST = 'localhost'
$env:STRESS_DB_PORT = '3306'
$env:STRESS_DB_USER = 'stress_app'
$env:STRESS_DB_PASSWORD = '<replace-with-database-password>'
$env:STRESS_DB_NAME = 'stress_db'

$env:DJANGO_SECRET_KEY = '<replace-with-a-long-random-django-key>'
$env:STRESS_JWT_SECRET = '<replace-with-at-least-32-random-bytes>'
$env:STRESS_ADMIN_PASSWORD = '<replace-for-first-start-only>'

$env:STRESS_DJANGO_DEBUG = 'true'
$env:STRESS_DJANGO_ALLOWED_HOSTS = '127.0.0.1,localhost'
$env:STRESS_CORS_ALLOWED_ORIGINS = 'http://127.0.0.1:5173'
