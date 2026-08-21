"""Gunicorn entry point: gunicorn -w 4 -b 127.0.0.1:8000 wsgi:app"""

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":  # pragma: no cover - local convenience
    app.run(host="127.0.0.1", port=5000)
