"""Admin panel: login, content management, inbox, settings, audit log, backup."""
import csv
import io
import re
import sqlite3
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import (Blueprint, Response, abort, current_app, flash, redirect, render_template, request,
                   send_file, send_from_directory, session, url_for)
from flask_login import current_user, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, limiter
from .models import (Application, Appointment, Article, AuditLog, ComplianceDate, Download, Faq, Opening, Page,
                     Query, Service, Setting, TeamMember, UsefulLink, User, utcnow)
from .security import UploadError, csv_safe, delete_upload, sanitize_html, save_upload, slugify, upload_dir

bp = Blueprint("admin", __name__, url_prefix="/admin")
IST = timedelta(hours=5, minutes=30)
_DUMMY_HASH = generate_password_hash("not-a-real-password")


# ---------------------------------------------------------------- resource definitions
class F:
    """One editable field of a content type."""

    def __init__(self, name, kind="text", label=None, required=False, choices=None, help="", max=400):
        self.name, self.kind, self.required, self.choices, self.help, self.max = name, kind, required, choices, help, max
        self.label = label or name.replace("_", " ").capitalize()


SEO = [F("meta_title", label="SEO title", max=160, help="Shown in the browser tab and search results."),
       F("meta_description", "textarea", label="SEO description", max=320, help="One or two sentences for search results.")]
IMG_HELP = "PNG, JPG or WEBP, up to 3 MB."

RESOURCES = {
    "pages": dict(
        model=Page, label="Pages", singular="page", order=[Page.id], can_create=False, can_delete=False,
        columns=[("title", "Title"), ("slug", "Page")],
        fields=[F("title", required=True, max=200), F("body_html", "richtext", label="Content"),
                F("image", "image", help=IMG_HELP)] + SEO),
    "services": dict(
        model=Service, label="Services", singular="service", order=[Service.sort_order, Service.id], sortable=True,
        columns=[("title", "Title"), ("is_visible", "Visible")],
        fields=[F("title", required=True, max=200), F("slug", "slug", label="URL name", help="Leave blank to generate from the title."),
                F("summary", "textarea", help="Short description shown on cards."), F("body_html", "richtext", label="Content"),
                F("image", "image", help=IMG_HELP), F("is_visible", "bool", label="Show on website")] + SEO),
    "team": dict(
        model=TeamMember, label="Partners & Team", singular="profile", order=[TeamMember.sort_order, TeamMember.id], sortable=True,
        columns=[("name", "Name"), ("designation", "Designation"), ("is_partner", "Partner"), ("is_visible", "Visible")],
        fields=[F("name", required=True, max=120), F("designation", max=120), F("qualifications", max=200, help="e.g. B.Com, FCA"),
                F("membership_no", label="ICAI membership no.", max=40), F("bio", "textarea", label="Profile", max=3000),
                F("image", "image", label="Photo", help=IMG_HELP), F("is_partner", "bool", label="Partner"),
                F("is_visible", "bool", label="Show on website")]),
    "articles": dict(
        model=Article, label="Articles & Updates", singular="article", order=[Article.published_at.desc()],
        columns=[("title", "Title"), ("category", "Type"), ("published_at", "Published"), ("is_published", "Live")],
        fields=[F("title", required=True, max=200), F("slug", "slug", label="URL name", help="Leave blank to generate from the title."),
                F("category", "select", label="Type", choices=[("article", "Article"), ("update", "News update")]),
                F("summary", "textarea"), F("body_html", "richtext", label="Content"), F("image", "image", help=IMG_HELP),
                F("published_at", "datetime", label="Publish date (IST)"), F("is_published", "bool", label="Published")] + SEO),
    "calendar": dict(
        model=ComplianceDate, label="Compliance Calendar", singular="due date", order=[ComplianceDate.due_date],
        columns=[("due_date", "Due date"), ("title", "Title"), ("category", "Category")],
        fields=[F("due_date", "date", required=True), F("title", required=True, max=200),
                F("category", max=40, help="e.g. GST, Income Tax, ROC, Payroll"), F("description", "textarea")]),
    "downloads": dict(
        model=Download, label="Downloads", singular="document", order=[Download.category, Download.title],
        columns=[("title", "Title"), ("category", "Category"), ("created_at", "Uploaded")],
        fields=[F("title", required=True, max=200), F("category", max=60, help="e.g. Forms, Checklists"),
                F("description", "textarea"), F("filename", "document", label="File", required=True,
                                                help="PDF, DOCX, XLSX, DOC or XLS, up to 10 MB.")]),
    "links": dict(
        model=UsefulLink, label="Useful Links", singular="link", order=[UsefulLink.sort_order, UsefulLink.id], sortable=True,
        columns=[("title", "Title"), ("url", "Address")],
        fields=[F("title", required=True, max=200), F("url", "url", label="Web address", required=True)]),
    "faqs": dict(
        model=Faq, label="FAQs", singular="FAQ", order=[Faq.sort_order, Faq.id], sortable=True,
        columns=[("question", "Question"), ("is_visible", "Visible")],
        fields=[F("question", required=True, max=300), F("answer", "richtext"), F("is_visible", "bool", label="Show on website")]),
    "openings": dict(
        model=Opening, label="Career Openings", singular="opening", order=[Opening.created_at.desc()],
        columns=[("title", "Title"), ("kind", "Type"), ("is_open", "Open")],
        fields=[F("title", required=True, max=200),
                F("kind", "select", label="Type", choices=[("Articleship", "Articleship"), ("Staff", "Staff")]),
                F("location", max=120), F("body_html", "richtext", label="Description"),
                F("is_open", "bool", label="Open for applications")]),
}
FILE_KINDS = {"image": "images", "document": "documents"}

INBOX = {
    "queries": dict(model=Query, label="Queries", columns=[("service", "Service"), ("message", "Message")]),
    "appointments": dict(model=Appointment, label="Appointment Requests",
                         columns=[("preferred_date", "Preferred date"), ("preferred_time", "Time"), ("service", "Service"), ("message", "Message")]),
    "applications": dict(model=Application, label="Job Applications", columns=[("position", "Position"), ("message", "Message")]),
}

SETTINGS_FORM = [
    ("firm_name", "Firm name", "text"), ("tagline", "Tagline", "text"), ("address", "Address", "text"),
    ("city", "City", "text"), ("state", "State", "text"), ("pincode", "PIN code", "text"),
    ("phone", "Phone", "text"), ("whatsapp", "WhatsApp number (with country code)", "text"), ("email", "Email", "text"),
    ("hours", "Office hours", "text"), ("frn", "Firm Registration Number", "text"), ("established", "Year established", "text"),
    ("map_embed_url", "Google Maps embed link", "text"), ("linkedin", "LinkedIn page link", "text"),
    ("disclaimer_popup", "Disclaimer pop-up text", "textarea"),
]


# ---------------------------------------------------------------- helpers
def audit(action, detail="", username=None):
    name = username or (current_user.username if current_user.is_authenticated else "-")
    db.session.add(AuditLog(username=name, action=action, detail=str(detail)[:500], ip=request.remote_addr or ""))


def resource(name):
    if name not in RESOURCES:
        abort(404)
    return RESOURCES[name]


def password_problems(password):
    problems = []
    if len(password) < 10:
        problems.append("Password must be at least 10 characters long.")
    if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        problems.append("Password must contain both letters and numbers.")
    return problems


@bp.before_request
def guard():
    """Every admin URL except the login page needs a live, non-idle session."""
    if request.endpoint == "admin.login":
        return None
    if not current_user.is_authenticated:
        return redirect(url_for("admin.login", next=request.path))
    last_seen = session.get("last_seen", 0)
    now = utcnow().timestamp()
    if now - last_seen > current_app.config["ADMIN_IDLE_MINUTES"] * 60:
        logout_user()
        session.clear()
        flash("You were signed out after a period of inactivity.", "warning")
        return redirect(url_for("admin.login"))
    session["last_seen"] = now
    if current_user.must_change_password and request.endpoint not in ("admin.change_password", "admin.logout"):
        return redirect(url_for("admin.change_password"))
    return None


@bp.app_context_processor
def inject_admin_nav():
    return {"admin_resources": RESOURCES, "admin_inbox": INBOX}


# ---------------------------------------------------------------- authentication
@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()[:64]
        password = request.form.get("password") or ""
        user = User.query.filter_by(username=username).first()
        now = utcnow()
        cfg = current_app.config
        if user and user.locked_until and user.locked_until > now:
            check_password_hash(_DUMMY_HASH, password)
            audit("login_blocked", "account locked", username)
            error = "This account is temporarily locked after repeated failed attempts. Try again later."
        elif user and check_password_hash(user.password_hash, password):
            user.failed_attempts, user.locked_until, user.last_login = 0, None, now
            session.clear()  # new session id on login
            login_user(user)
            session.permanent = True
            session["last_seen"] = now.timestamp()
            audit("login", username=username)
            db.session.commit()
            target = request.args.get("next", "")
            if not target.startswith("/admin") or target.startswith("//"):
                target = url_for("admin.dashboard")
            return redirect(target)
        else:
            if user:
                user.failed_attempts += 1
                if user.failed_attempts >= cfg["LOCKOUT_ATTEMPTS"]:
                    user.locked_until = now + timedelta(minutes=cfg["LOCKOUT_MINUTES"])
                    user.failed_attempts = 0
                    audit("lockout", f"locked for {cfg['LOCKOUT_MINUTES']} minutes", username)
            else:
                check_password_hash(_DUMMY_HASH, password)  # keep timing similar for unknown users
            audit("login_failed", username=username)
            error = "Incorrect username or password."
        db.session.commit()
    return render_template("admin/login.html", error=error), (401 if error else 200)


@bp.route("/logout", methods=["POST"])
def logout():
    audit("logout")
    db.session.commit()
    logout_user()
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("admin.login"))


@bp.route("/change-password", methods=["GET", "POST"])
def change_password():
    errors = []
    if request.method == "POST":
        current, new, confirm = (request.form.get(k) or "" for k in ("current", "new", "confirm"))
        if not check_password_hash(current_user.password_hash, current):
            errors.append("Current password is incorrect.")
        errors += password_problems(new)
        if new != confirm:
            errors.append("The new passwords do not match.")
        if new and new == current:
            errors.append("The new password must be different from the current one.")
        if not errors:
            current_user.password_hash = generate_password_hash(new)
            current_user.must_change_password = False
            audit("password_changed")
            db.session.commit()
            flash("Password updated.", "success")
            return redirect(url_for("admin.dashboard"))
    return render_template("admin/change_password.html", errors=errors), (400 if errors else 200)


# ---------------------------------------------------------------- dashboard
@bp.route("/")
def dashboard():
    counts = {key: cfg["model"].query.filter_by(handled=False).count() for key, cfg in INBOX.items()}
    recent = AuditLog.query.order_by(AuditLog.id.desc()).limit(8).all()
    return render_template("admin/dashboard.html", counts=counts, recent=recent)


# ---------------------------------------------------------------- generic content management
def unique_slug(model, wanted, obj):
    slug, n = wanted, 2
    while True:
        other = model.query.filter_by(slug=slug).first()
        if not other or other.id == obj.id:
            return slug
        slug, n = f"{wanted}-{n}", n + 1


def apply_form(res, obj):
    """Copy the submitted form into obj. Returns (errors, new_files, old_files)."""
    errors, added, stale = [], [], []
    for f in res["fields"]:
        if f.kind == "bool":
            setattr(obj, f.name, bool(request.form.get(f.name)))
            continue
        if f.kind in FILE_KINDS:
            kind, upload = FILE_KINDS[f.kind], request.files.get(f.name)
            existing = getattr(obj, f.name) or ""
            if upload and upload.filename:
                try:
                    name = save_upload(upload, kind)
                except UploadError as exc:
                    errors.append(f"{f.label}: {exc}")
                    continue
                added.append((kind, name))
                if existing:
                    stale.append((kind, existing))
                setattr(obj, f.name, name)
            elif request.form.get(f.name + "_remove") and not f.required:
                if existing:
                    stale.append((kind, existing))
                setattr(obj, f.name, "")
            elif f.required and not existing:
                errors.append(f"{f.label}: please choose a file.")
            continue

        raw = (request.form.get(f.name) or "").strip()
        value = raw
        if f.kind == "richtext":
            value = sanitize_html(raw)
        elif f.kind == "date":
            try:
                value = datetime.strptime(raw, "%Y-%m-%d").date()
            except ValueError:
                value = None
                if raw or f.required:
                    errors.append(f"{f.label}: please enter a valid date.")
                    continue
        elif f.kind == "datetime":
            try:
                value = datetime.strptime(raw, "%Y-%m-%dT%H:%M") - IST
            except ValueError:
                value = getattr(obj, f.name) or utcnow()
        elif f.kind == "url":
            if raw and not re.match(r"^https?://[^\s]+$", raw):
                errors.append(f"{f.label}: must start with http:// or https://")
                continue
        elif f.kind == "select":
            if raw not in [c[0] for c in f.choices]:
                value = f.choices[0][0]
        elif f.kind == "slug":
            value = unique_slug(res["model"], slugify(raw or request.form.get("title", "")), obj)
        else:
            value = raw[: f.max]
        if f.required and not value:
            errors.append(f"{f.label} is required.")
            continue
        setattr(obj, f.name, value)
    return errors, added, stale


def describe(obj):
    return getattr(obj, "title", None) or getattr(obj, "name", None) or getattr(obj, "question", None) or f"#{obj.id}"


@bp.route("/content/<name>")
def content_list(name):
    res = resource(name)
    items = res["model"].query.order_by(*res["order"]).all()
    return render_template("admin/list.html", res=res, name=name, items=items)


@bp.route("/content/<name>/new", methods=["GET", "POST"])
@bp.route("/content/<name>/<int:item_id>", methods=["GET", "POST"])
def content_edit(name, item_id=None):
    res = resource(name)
    model = res["model"]
    if item_id is None:
        if not res.get("can_create", True):
            abort(404)
        obj = model()
        for f in res["fields"]:  # sensible defaults on the blank form
            if f.kind == "bool":
                setattr(obj, f.name, f.name != "is_partner")
    else:
        obj = db.session.get(model, item_id) or abort(404)
    errors = []
    if request.method == "POST":
        with db.session.no_autoflush:
            errors, added, stale = apply_form(res, obj)
        if errors:
            db.session.rollback()
            for kind, fname in added:
                delete_upload(kind, fname)
        else:
            if item_id is None:
                if res.get("sortable"):
                    obj.sort_order = model.query.count() + 1
                db.session.add(obj)
            db.session.flush()
            audit("created" if item_id is None else "updated", f"{res['singular']}: {describe(obj)}")
            db.session.commit()
            for kind, fname in stale:
                delete_upload(kind, fname)
            flash(f"Saved {res['singular']}.", "success")
            return redirect(url_for("admin.content_list", name=name))
    return render_template("admin/form.html", res=res, name=name, obj=obj, is_new=item_id is None,
                           errors=errors, IST=IST), (400 if errors else 200)


@bp.route("/content/<name>/<int:item_id>/delete", methods=["POST"])
def content_delete(name, item_id):
    res = resource(name)
    if not res.get("can_delete", True):
        abort(404)
    obj = db.session.get(res["model"], item_id) or abort(404)
    files = [(FILE_KINDS[f.kind], getattr(obj, f.name)) for f in res["fields"] if f.kind in FILE_KINDS]
    audit("deleted", f"{res['singular']}: {describe(obj)}")
    db.session.delete(obj)
    db.session.commit()
    for kind, fname in files:
        delete_upload(kind, fname)
    flash(f"Deleted {res['singular']}.", "success")
    return redirect(url_for("admin.content_list", name=name))


@bp.route("/content/<name>/<int:item_id>/move/<direction>", methods=["POST"])
def content_move(name, item_id, direction):
    res = resource(name)
    if not res.get("sortable") or direction not in ("up", "down"):
        abort(404)
    items = res["model"].query.order_by(*res["order"]).all()
    index = next((i for i, it in enumerate(items) if it.id == item_id), None)
    if index is None:
        abort(404)
    swap = index - 1 if direction == "up" else index + 1
    if 0 <= swap < len(items):
        items[index], items[swap] = items[swap], items[index]
    for position, item in enumerate(items, 1):
        item.sort_order = position
    audit("reordered", f"{res['label']}: {describe(items[min(max(swap, 0), len(items) - 1)])}")
    db.session.commit()
    return redirect(url_for("admin.content_list", name=name))


# ---------------------------------------------------------------- inbox
def inbox(kind):
    if kind not in INBOX:
        abort(404)
    return INBOX[kind]


@bp.route("/inbox/<kind>")
def inbox_list(kind):
    cfg = inbox(kind)
    items = cfg["model"].query.order_by(cfg["model"].created_at.desc()).all()
    return render_template("admin/inbox.html", cfg=cfg, kind=kind, items=items)


@bp.route("/inbox/<kind>/<int:item_id>/handled", methods=["POST"])
def inbox_toggle(kind, item_id):
    cfg = inbox(kind)
    item = db.session.get(cfg["model"], item_id) or abort(404)
    item.handled = not item.handled
    audit("marked_handled" if item.handled else "marked_open", f"{cfg['label']} #{item.id}")
    db.session.commit()
    return redirect(url_for("admin.inbox_list", kind=kind))


@bp.route("/inbox/<kind>/<int:item_id>/delete", methods=["POST"])
def inbox_delete(kind, item_id):
    cfg = inbox(kind)
    item = db.session.get(cfg["model"], item_id) or abort(404)
    resume = getattr(item, "resume", "")
    audit("deleted", f"{cfg['label']} #{item.id}")
    db.session.delete(item)
    db.session.commit()
    delete_upload("resumes", resume)
    flash("Entry deleted.", "success")
    return redirect(url_for("admin.inbox_list", kind=kind))


@bp.route("/inbox/<kind>/export.csv")
def inbox_export(kind):
    cfg = inbox(kind)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Received (IST)", "Name", "Phone", "Email"] + [label for _, label in cfg["columns"]] + ["Handled"])
    for item in cfg["model"].query.order_by(cfg["model"].created_at.desc()):
        row = [(item.created_at + IST).strftime("%Y-%m-%d %H:%M"), item.name, item.phone, item.email]
        row += [getattr(item, attr) for attr, _ in cfg["columns"]] + ["Yes" if item.handled else "No"]
        writer.writerow([csv_safe(v) for v in row])
    audit("exported", cfg["label"])
    db.session.commit()
    return Response("﻿" + out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={kind}-{date.today().isoformat()}.csv"})


@bp.route("/inbox/applications/<int:item_id>/resume")
def resume(item_id):
    item = db.session.get(Application, item_id) or abort(404)
    if not item.resume:
        abort(404)
    safe = re.sub(r"[^A-Za-z0-9]+", "-", item.name).strip("-") or "applicant"
    return send_from_directory(upload_dir("resumes"), item.resume, as_attachment=True, download_name=f"resume-{safe}.pdf")


# ---------------------------------------------------------------- settings, audit, backup
@bp.route("/settings", methods=["GET", "POST"])
def settings():
    values = {s.key: s for s in Setting.query.all()}
    errors = []
    if request.method == "POST":
        submitted = {key: (request.form.get(key) or "").strip()[:2000] for key, _, _ in SETTINGS_FORM}
        if not submitted["firm_name"]:
            errors.append("Firm name is required.")
        for key in ("map_embed_url", "linkedin"):
            if submitted[key] and not submitted[key].startswith("https://"):
                errors.append("Links must start with https://")
        if submitted["map_embed_url"] and not re.match(r"^https://(www|maps)\.google\.com/", submitted["map_embed_url"]):
            errors.append("The map link must be a Google Maps embed link.")
        if not errors:
            for key, value in submitted.items():
                if key in values:
                    values[key].value = value
                else:
                    db.session.add(Setting(key=key, value=value))
            audit("updated", "firm details and settings")
            db.session.commit()
            flash("Settings saved.", "success")
            return redirect(url_for("admin.settings"))
    current = {key: (request.form.get(key) if request.method == "POST" else (values[key].value if key in values else ""))
               for key, _, _ in SETTINGS_FORM}
    return render_template("admin/settings.html", fields=SETTINGS_FORM, current=current, errors=errors), (400 if errors else 200)


@bp.route("/audit-log")
def audit_log():
    entries = AuditLog.query.order_by(AuditLog.id.desc()).limit(500).all()
    return render_template("admin/audit.html", entries=entries)


@bp.route("/backup", methods=["POST"])
def backup():
    """Consistent snapshot of the SQLite database via the online backup API."""
    audit("backup_downloaded")
    db.session.commit()
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "backup.db"
        src = sqlite3.connect(current_app.config["DB_PATH"])
        dst = sqlite3.connect(target)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        data = io.BytesIO(target.read_bytes())
    stamp = (utcnow() + IST).strftime("%Y%m%d-%H%M")
    return send_file(data, as_attachment=True, download_name=f"shukla-mishra-site-backup-{stamp}.db",
                     mimetype="application/octet-stream")
