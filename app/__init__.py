"""Application factory for the Shukla Mishra & Co website."""
import os
import secrets
from datetime import timedelta
from pathlib import Path

import click
from flask import Flask, redirect, render_template, request
from flask_wtf.csrf import CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix

from .extensions import csrf, db, limiter, login_manager

BASE_DIR = Path(__file__).resolve().parent.parent

CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; frame-src https://www.google.com https://maps.google.com; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)


def _flag(name, default="0"):
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def _secret_key(data_dir):
    """Use SECRET_KEY from the environment, else a key generated once and kept on disk."""
    key = os.environ.get("SECRET_KEY")
    if key:
        return key
    key_file = data_dir / "secret_key"
    if not key_file.exists():
        key_file.write_text(secrets.token_hex(32), encoding="utf-8")
    return key_file.read_text(encoding="utf-8").strip()


def create_app(test_config=None):
    test_config = test_config or {}
    data_dir = Path(test_config.get("DATA_DIR") or os.environ.get("SMC_DATA_DIR") or BASE_DIR / "instance").resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__, instance_path=str(data_dir))
    force_https = _flag("FORCE_HTTPS")
    app.config.update(
        SECRET_KEY=_secret_key(data_dir),
        DATA_DIR=str(data_dir),
        DB_PATH=str(data_dir / "site.db"),
        SQLALCHEMY_DATABASE_URI="sqlite:///" + (data_dir / "site.db").as_posix(),
        UPLOAD_DIR=str(data_dir / "uploads"),
        MAX_CONTENT_LENGTH=12 * 1024 * 1024,
        FORCE_HTTPS=force_https,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=force_https,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        ADMIN_IDLE_MINUTES=int(os.environ.get("ADMIN_IDLE_MINUTES", "30")),
        LOCKOUT_ATTEMPTS=5,
        LOCKOUT_MINUTES=15,
        SITE_URL=os.environ.get("SITE_URL", "").rstrip("/"),
        MAIL_SERVER=os.environ.get("MAIL_SERVER", ""),
        MAIL_PORT=int(os.environ.get("MAIL_PORT", "587")),
        MAIL_USERNAME=os.environ.get("MAIL_USERNAME", ""),
        MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD", ""),
        MAIL_FROM=os.environ.get("MAIL_FROM", ""),
        MAIL_TO=os.environ.get("MAIL_TO", ""),
        MAIL_USE_SSL=_flag("MAIL_USE_SSL"),
    )
    app.config.update(test_config)

    if _flag("BEHIND_PROXY"):  # IIS / reverse proxy forwards the real scheme and client IP
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "admin.login"

    from . import models
    from .admin import bp as admin_bp
    from .public import bp as public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    @app.before_request
    def enforce_https():
        if app.config["FORCE_HTTPS"] and not request.is_secure:
            return redirect(request.url.replace("http://", "https://", 1), code=301)

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("Content-Security-Policy", CSP)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
        if request.is_secure:
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.path.startswith("/admin"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    def _error(code, title, text):
        return render_template("error.html", code=code, title=title, text=text), code

    app.register_error_handler(404, lambda e: _error(404, "Page not found", "The page you are looking for does not exist or has been moved."))
    app.register_error_handler(413, lambda e: _error(413, "File too large", "The uploaded file exceeds the size limit."))
    app.register_error_handler(429, lambda e: _error(429, "Too many requests", "Please wait a minute and try again."))
    app.register_error_handler(500, lambda e: _error(500, "Something went wrong", "Please try again later."))
    app.register_error_handler(CSRFError, lambda e: _error(400, "Session expired", "Your form session expired. Please go back, refresh the page and submit again."))

    @app.template_filter("ist")
    def ist(dt, fmt="%d %b %Y, %I:%M %p"):
        """Stored timestamps are UTC; show them in Indian Standard Time."""
        return (dt + timedelta(hours=5, minutes=30)).strftime(fmt) if dt else ""

    @app.template_filter("datefmt")
    def datefmt(d, fmt="%d %b %Y"):
        return d.strftime(fmt) if d else ""

    @app.cli.command("init-db")
    def init_db():
        """Create tables, load starter content and create the admin user."""
        from .seed import seed_all

        db.create_all()
        password = seed_all()
        click.echo("Database ready: " + app.config["DB_PATH"])
        if password:
            click.echo("\n  Admin login created")
            click.echo("    Username: admin")
            click.echo("    Temporary password: " + password)
            click.echo("  You will be asked to set a new password at first login.\n")
        else:
            click.echo("Admin user already exists (use 'flask reset-admin' to reset the password).")

    @app.cli.command("reset-admin")
    @click.option("--username", default="admin")
    def reset_admin(username):
        """Reset an admin password to a new temporary one and clear any lockout."""
        from .seed import set_temp_password

        password = set_temp_password(username)
        click.echo(f"Username: {username}\nTemporary password: {password}")

    return app
