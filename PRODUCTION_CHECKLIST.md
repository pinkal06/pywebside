# RetiyaBazar production checklist

- [ ] Set a unique `SECRET_KEY` in the environment.
- [ ] Set `DEBUG=False`.
- [ ] Set production `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
- [ ] Configure MySQL through `DB_*` environment variables.
- [ ] Configure SMTP through `EMAIL_*` environment variables.
- [ ] Run `python manage.py migrate`.
- [ ] Run `python manage.py collectstatic --noinput`.
- [ ] Configure HTTPS before enabling secure cookies and redirects.
- [ ] Configure a process manager with Gunicorn and a reverse proxy such as Nginx.
- [ ] Back up the database and `media/` files.
- [ ] Review logs without storing passwords, tokens, or payment secrets.
- [ ] Run `python manage.py check --deploy` and the test suite.
