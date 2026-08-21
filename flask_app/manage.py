"""Flask CLI entry point: `export FLASK_APP=manage.py` then `flask db upgrade`."""

from dotenv import load_dotenv

load_dotenv()

from app import create_app, db  # noqa: E402
from app.models import EmailToken, Image, User  # noqa: E402,F401

app = create_app()


@app.shell_context_processor
def shell_context():
    return {"db": db, "User": User, "Image": Image, "EmailToken": EmailToken}
