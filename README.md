# ADM Cloud

ADM Cloud is the image-hosting product in the ADM family. Users can register with email, sign in with Google or GitHub, verify accounts, upload images to Cloudinary, organize them into folders, compress images before upload, and share branded public links.

## Run locally

```powershell
cd flask_app
..\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:FLASK_APP = "manage.py"
$env:FLASK_ENV = "development"
python -m flask db upgrade
python -m flask run --host 127.0.0.1 --port 5000
```

Open http://127.0.0.1:5000.

## Deploy on Render

The root `render.yaml` defines the Flask web service, PostgreSQL database, migrations, Gunicorn command, and health check. Add SMTP, Cloudinary, Google OAuth, and GitHub OAuth secrets in Render Environment Variables. Never commit `.env` or provider secrets.

The application code and deployment files live under `flask_app/`.
