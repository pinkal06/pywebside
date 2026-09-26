# Deployment guide

1. Create a Python virtual environment and install `requirements.txt`.
2. Create a production environment from `.env.example`; never commit the real file.
3. Provision MySQL and set `USE_MYSQL=True` plus the `DB_*` variables.
4. Run `python manage.py migrate` and create a superuser.
5. Run `python manage.py collectstatic --noinput`.
6. Run `python manage.py check --deploy`.
7. Serve `config.wsgi:application` with Gunicorn behind Nginx.
8. Configure Nginx to serve `/static/` from `staticfiles/` and `/media/` from `media/`.
9. Configure HTTPS, then keep `SECURE_SSL_REDIRECT=True`.
10. Verify `/health/`, login, public product pages, admin permissions, and backups.

The Django development server (`runserver`) is for local development only.
