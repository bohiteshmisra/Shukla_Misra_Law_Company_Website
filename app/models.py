"""Database models. SQLite via SQLAlchemy; one file, no separate DB server."""
from datetime import datetime, timezone

from flask_login import UserMixin

from .extensions import db


def utcnow():
    """Naive UTC timestamp (SQLite stores naive datetimes)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    must_change_password = db.Column(db.Boolean, default=True, nullable=False)
    failed_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)


class Setting(db.Model):
    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text, default="", nullable=False)


class SeoMixin:
    meta_title = db.Column(db.String(160), default="")
    meta_description = db.Column(db.String(320), default="")


class Page(SeoMixin, db.Model):
    """Fixed site pages (home, about, contact, legal ...) editable by the admin."""
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(64), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body_html = db.Column(db.Text, default="")
    image = db.Column(db.String(120), default="")


class Service(SeoMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.String(400), default="")
    body_html = db.Column(db.Text, default="")
    image = db.Column(db.String(120), default="")
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_visible = db.Column(db.Boolean, default=True, nullable=False)


class TeamMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    designation = db.Column(db.String(120), default="")
    qualifications = db.Column(db.String(200), default="")
    membership_no = db.Column(db.String(40), default="")
    bio = db.Column(db.Text, default="")
    image = db.Column(db.String(120), default="")
    is_partner = db.Column(db.Boolean, default=False, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_visible = db.Column(db.Boolean, default=True, nullable=False)


class Article(SeoMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(160), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(20), default="article", nullable=False)  # article | update
    summary = db.Column(db.String(400), default="")
    body_html = db.Column(db.Text, default="")
    image = db.Column(db.String(120), default="")
    is_published = db.Column(db.Boolean, default=True, nullable=False)
    published_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class ComplianceDate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    due_date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(40), default="")
    description = db.Column(db.String(400), default="")


class Download(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(60), default="")
    description = db.Column(db.String(400), default="")
    filename = db.Column(db.String(120), default="")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class UsefulLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(400), nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)


class Faq(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(300), nullable=False)
    answer = db.Column(db.Text, default="")
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_visible = db.Column(db.Boolean, default=True, nullable=False)


class Opening(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    kind = db.Column(db.String(40), default="Staff")  # Articleship | Staff
    location = db.Column(db.String(120), default="Lucknow")
    body_html = db.Column(db.Text, default="")
    is_open = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class SubmissionMixin:
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, default="")
    consent = db.Column(db.Boolean, default=False, nullable=False)
    handled = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Query(SubmissionMixin, db.Model):
    __tablename__ = "client_query"
    service = db.Column(db.String(200), default="")


class Appointment(SubmissionMixin, db.Model):
    service = db.Column(db.String(200), default="")
    preferred_date = db.Column(db.Date)
    preferred_time = db.Column(db.String(40), default="")


class Application(SubmissionMixin, db.Model):
    __tablename__ = "job_application"
    position = db.Column(db.String(200), default="")
    resume = db.Column(db.String(120), default="")


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    username = db.Column(db.String(64), default="-")
    action = db.Column(db.String(60), nullable=False)
    detail = db.Column(db.String(500), default="")
    ip = db.Column(db.String(64), default="")
