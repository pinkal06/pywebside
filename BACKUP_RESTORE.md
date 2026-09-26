# Backup and restore

## MySQL

Use a protected shell where the password is supplied interactively or by the
database client configuration:

```bash
mysqldump -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p "$DB_NAME" > retiyabazar.sql
mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p "$DB_NAME" < retiyabazar.sql
```

## Media

Back up the `media/` directory separately and restore it to the configured
`MEDIA_ROOT`. Do not include `.env` or secrets in backups shared with others.

After restoring, run migrations, check file permissions, and verify `/health/`
and representative product images.
