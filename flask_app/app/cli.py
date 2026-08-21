"""Management commands. No credentials are hardcoded anywhere."""

import os

import click
from flask import Flask

from .extensions import db
from .models import User, UserRole


def register_cli(app: Flask) -> None:
    @app.cli.command("create-admin")
    @click.option("--email", default=None, help="Administrator email address.")
    @click.option("--password", default=None, help="Password (prompted if omitted).")
    def create_admin(email, password):
        """Create or promote an administrator account."""
        email = User.normalize_email(email or os.environ.get("ADMIN_EMAIL") or click.prompt("Email"))
        password = password or os.environ.get("ADMIN_PASSWORD")
        if not password:
            password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
        if len(password) < 10:
            raise click.ClickException("Password must be at least 10 characters.")

        user = User.query.filter_by(email=email).first()
        if user:
            user.role = UserRole.ADMIN
            user.email_verified = True
            user.is_blocked = False
            user.set_password(password)
            click.echo(f"Existing account promoted to administrator: {email}")
        else:
            user = User(email=email, role=UserRole.ADMIN, email_verified=True)
            user.set_password(password)
            db.session.add(user)
            click.echo(f"Administrator created: {email}")
        db.session.commit()

    @app.cli.command("list-admins")
    def list_admins():
        """List administrator accounts."""
        for user in User.query.filter_by(role=UserRole.ADMIN).all():
            click.echo(f"{user.id}\t{user.email}\tblocked={user.is_blocked}")
