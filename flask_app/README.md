# Image Hosting Platform

A self-hosted, white-label image hosting service: users register, confirm their
email, upload images and get a permanent public link (`https://yourdomain.com/i/<id>`)
they can use on any website. Admins manage users and see platform statistics.

The project is fully independent — Flask + PostgreSQL + your own Cloudinary and
SMTP accounts. There is no managed backend, no vendor SDK in the browser, and no
third-party branding in the UI or emails.

## Architecture

```
Internet -> Nginx -> Gunicorn -> Flask -> PostgreSQL
                                   +-> Cloudinary (image storage / CDN)
                                   +-> SMTP (verification email)
```

```
app/
  __init__.py    application factory, error handlers, branding context
  config.py      Development / Production / Testing, all env-driven
  extensions.py  db, migrate, login_manager, csrf, limiter
  cli.py         `flask create-admin`, `flask list-admins`
  forms.py       WTForms + CSRF
  models/        user.py, image.py, token.py
  routes/        public, auth, dashboard, images (JSON), admin, api
  services/      storage_service, image_service, image_validation, email_service, tokens
  utils/         decorators, security headers, formatting
  templates/     Jinja templates (public, auth, dashboard, admin, email, errors)
  static/        css/app.css, js/app.js
migrations/      Alembic
tests/           pytest suite
deploy/          nginx.conf.example, imagehost.service.example
wsgi.py          Gunicorn entry point
manage.py        Flask CLI entry point
```

`storage_service.py` is the only module that knows about Cloudinary; swapping the
provider means rewriting that one file.

## Local development

```bash
cd flask_app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in real values
export FLASK_APP=manage.py FLASK_ENV=development
flask db upgrade
flask create-admin            # prompts for email + password
flask run                     # http://localhost:5000
```

Run tests (SQLite in memory, Cloudinary and SMTP mocked):

```bash
python -m pytest -q
```

## Environment variables

| Variable | Purpose |
| --- | --- |
| `FLASK_ENV` | `development`, `production` or `testing` |
| `SECRET_KEY` | Session/CSRF signing key — long random string |
| `DATABASE_URL` | e.g. `postgresql+psycopg2://user:pass@host:5432/db` |
| `APP_NAME`, `APP_BASE_URL` | Product name and canonical URL |
| `APP_LOGO_URL`, `APP_FAVICON_URL` | Branding assets |
| `APP_PRIMARY_COLOR`, `APP_SECONDARY_COLOR` | Theme colours |
| `SUPPORT_EMAIL` | Shown in footer and emails |
| `PUBLIC_IMAGE_BASE_URL` | Optional image subdomain, e.g. `https://img.example.com` |
| `CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET` | Storage credentials (server only) |
| `CLOUDINARY_UPLOAD_FOLDER` | Folder assets are stored under |
| `CLOUDINARY_THUMB_TRANSFORM` | Gallery thumbnail transform, e.g. `c_fill,w_400,h_400,q_auto,f_auto` |
| `SMTP_HOST/PORT/USERNAME/PASSWORD/FROM_EMAIL/USE_TLS/USE_SSL` | Email delivery |
| `UPLOAD_MAX_SIZE` | Max bytes per upload (default 10 MB) |
| `ALLOWED_IMAGE_TYPES` | Comma-separated MIME allow-list |
| `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE`, `PERMANENT_SESSION_LIFETIME` | Cookie policy |
| `VERIFICATION_TOKEN_MAX_AGE` | Verification link lifetime in seconds |
| `RATELIMIT_ENABLED`, `RATELIMIT_STORAGE_URI`, `RATELIMIT_*` | Rate limits (use Redis in production) |

`.env` is git-ignored; only `.env.example` is committed.

## PostgreSQL setup

```sql
CREATE USER imagehost WITH PASSWORD 'strong-password';
CREATE DATABASE imagehost OWNER imagehost;
```

Set `DATABASE_URL=postgresql+psycopg2://imagehost:strong-password@localhost:5432/imagehost`.

## Cloudinary setup

Create an account, open the dashboard and copy the cloud name, API key and API
secret into `.env`. The secret never leaves the server — uploads always go
browser → Flask → Cloudinary.

## SMTP setup

Any provider works (Postmark, SES, Mailgun, your own server). Set the `SMTP_*`
variables; use port 587 with `SMTP_USE_TLS=true`, or 465 with `SMTP_USE_SSL=true`.

## Migrations

```bash
flask db migrate -m "describe change"   # create a migration after model changes
flask db upgrade                        # apply
flask db downgrade                      # roll back one revision
```

## First administrator

```bash
flask create-admin --email you@example.com    # password is prompted, never stored in code
```

Self-registration always creates a normal `user`; the role field cannot be set
through any HTTP request.

## Production deployment (Ubuntu VPS)

```bash
sudo apt update && sudo apt install -y python3-venv python3-dev build-essential \
  libpq-dev postgresql nginx certbot python3-certbot-nginx
sudo adduser --system --group imagehost
sudo mkdir -p /srv/imagehost && sudo chown imagehost:imagehost /srv/imagehost
# copy the project to /srv/imagehost, then as the imagehost user:
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in production values, FLASK_ENV=production,
                       # SESSION_COOKIE_SECURE=true, APP_BASE_URL=https://yourdomain.com
FLASK_APP=manage.py .venv/bin/flask db upgrade
FLASK_APP=manage.py .venv/bin/flask create-admin
```

Gunicorn:

```bash
.venv/bin/gunicorn --workers 4 --timeout 90 --bind 127.0.0.1:8000 wsgi:app
```

systemd and Nginx: copy `deploy/imagehost.service.example` to
`/etc/systemd/system/imagehost.service` and `deploy/nginx.conf.example` to
`/etc/nginx/sites-available/imagehost`, adjust the domains and paths, then:

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now imagehost
sudo ln -s /etc/nginx/sites-available/imagehost /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d yourdomain.com -d img.yourdomain.com
```

Keep Nginx's `client_max_body_size` at or above `UPLOAD_MAX_SIZE`.

## Security notes

- Passwords hashed with Werkzeug PBKDF2; plaintext is never stored or logged.
- Session cookies are HTTPOnly, SameSite and Secure in production.
- CSRF protection on every state-changing request (JSON calls send `X-CSRFToken`).
- Uploads validated by extension, real decoded format and size; filenames are
  regenerated server-side.
- Ownership and admin role are checked server-side on every request; hidden UI is
  never treated as protection.
- Verification tokens are random, hashed at rest, single-use and expiring.
- Rate limits on login, registration, verification resend and upload. Use
  `RATELIMIT_STORAGE_URI=redis://…` when running more than one worker.
- Production responses contain no stack traces; errors are logged server-side.
- If a database write fails after an upload, the stored asset is deleted so no
  orphan remains.

## Customising branding

Everything user-visible comes from environment variables (`APP_NAME`,
`APP_LOGO_URL`, `APP_FAVICON_URL`, colours, support email) injected into every
template by a single context processor in `app/__init__.py`. For deeper visual
changes edit `app/static/css/app.css` — the palette is driven by the `--brand`
and `--brand-2` custom properties set from your configured colours.
