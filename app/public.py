"""Public website: pages, forms, media, sitemap."""
import re
import smtplib
import threading
from datetime import date, datetime
from email.message import EmailMessage

from flask import (Blueprint, Response, abort, current_app, flash, redirect, render_template, request,
                   send_from_directory, url_for)

from .extensions import db, limiter
from .models import (Application, Appointment, Article, ComplianceDate, Download, Faq, Opening, Page, Query,
                     Service, Setting, TeamMember, UsefulLink)
from .security import PUBLIC_KINDS, UploadError, check_captcha, new_captcha, save_upload, upload_dir

bp = Blueprint("public", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
PHONE_RE = re.compile(r"^[0-9+\-\s()]{7,20}$")


# ---------------------------------------------------------------- helpers
@bp.app_context_processor
def inject_site():
    site = {s.key: s.value for s in Setting.query.all()}
    nav_services = Service.query.filter_by(is_visible=True).order_by(Service.sort_order, Service.id).all()
    return {"site": site, "nav_services": nav_services, "current_year": date.today().year, "site_root": site_url()}


def get_page(slug):
    page = Page.query.filter_by(slug=slug).first()
    if not page:
        abort(404)
    return page


def field(name, limit=200):
    return (request.form.get(name) or "").strip()[:limit]


def notify(subject, lines):
    """Email the firm about a new submission. Skipped silently when SMTP is not configured."""
    cfg = current_app.config
    if not (cfg["MAIL_SERVER"] and cfg["MAIL_TO"]) or cfg.get("TESTING"):
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["MAIL_FROM"] or cfg["MAIL_USERNAME"]
    msg["To"] = cfg["MAIL_TO"]
    msg.set_content("\n".join(lines) + "\n\nView it in the website admin panel.")
    logger = current_app.logger

    def send():
        try:
            smtp_cls = smtplib.SMTP_SSL if cfg["MAIL_USE_SSL"] else smtplib.SMTP
            with smtp_cls(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=20) as smtp:
                if not cfg["MAIL_USE_SSL"]:
                    smtp.starttls()
                if cfg["MAIL_USERNAME"]:
                    smtp.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
                smtp.send_message(msg)
        except Exception as exc:  # never let mail problems break the form
            logger.warning("Notification email failed: %s", exc)

    threading.Thread(target=send, daemon=True).start()


def validate_contact(key, errors):
    """Checks shared by all public forms. Returns (name, phone, email, message)."""
    name, phone, email, message = field("name", 120), field("phone", 30), field("email", 200), field("message", 3000)
    if len(name) < 2:
        errors.append("Please enter your name.")
    if not PHONE_RE.match(phone):
        errors.append("Please enter a valid phone number.")
    if not EMAIL_RE.match(email):
        errors.append("Please enter a valid email address.")
    if not request.form.get("consent"):
        errors.append("Please give your consent to the use of your details for responding to you.")
    if not check_captcha(key, request.form.get("captcha")):
        errors.append("The answer to the verification question was incorrect. Please try again.")
    return name, phone, email, message


def is_bot():
    """Hidden honeypot field: humans leave it empty."""
    return bool(request.form.get("website"))


# ---------------------------------------------------------------- pages
@bp.route("/")
def home():
    return render_template(
        "home.html", page=get_page("home"),
        services=Service.query.filter_by(is_visible=True).order_by(Service.sort_order, Service.id).all(),
        due_dates=ComplianceDate.query.filter(ComplianceDate.due_date >= date.today()).order_by(ComplianceDate.due_date).limit(5).all(),
        articles=Article.query.filter_by(is_published=True).order_by(Article.published_at.desc()).limit(3).all(),
    )


@bp.route("/about")
def about():
    team = TeamMember.query.filter_by(is_visible=True).order_by(TeamMember.is_partner.desc(), TeamMember.sort_order, TeamMember.id).all()
    return render_template("about.html", page=get_page("about"), team=team)


@bp.route("/services")
def services():
    items = Service.query.filter_by(is_visible=True).order_by(Service.sort_order, Service.id).all()
    return render_template("services.html", page=get_page("services"), services=items)


@bp.route("/services/<slug>")
def service_detail(slug):
    service = Service.query.filter_by(slug=slug, is_visible=True).first_or_404()
    return render_template("service_detail.html", service=service, page=service)


@bp.route("/knowledge")
def knowledge():
    return render_template(
        "knowledge.html", page=get_page("knowledge"),
        articles=Article.query.filter_by(is_published=True).order_by(Article.published_at.desc()).all(),
        due_dates=ComplianceDate.query.filter(ComplianceDate.due_date >= date.today()).order_by(ComplianceDate.due_date).all(),
        links=UsefulLink.query.order_by(UsefulLink.sort_order, UsefulLink.id).all(),
        downloads=Download.query.order_by(Download.category, Download.title).all(),
    )


@bp.route("/knowledge/<slug>")
def article(slug):
    item = Article.query.filter_by(slug=slug, is_published=True).first_or_404()
    return render_template("article.html", article=item, page=item)


def render_support(errors=None, which=None, status=200):
    return render_template(
        "support.html", page=get_page("support"), errors=errors or [], which=which, form=request.form,
        faqs=Faq.query.filter_by(is_visible=True).order_by(Faq.sort_order, Faq.id).all(),
        captcha_query=new_captcha("query"), captcha_appointment=new_captcha("appointment"),
        today=date.today().isoformat(),
    ), status


@bp.route("/support")
def support():
    return render_support()


@bp.route("/support/query", methods=["POST"])
@limiter.limit("5 per minute; 30 per hour")
def submit_query():
    errors = []
    name, phone, email, message = validate_contact("query", errors)
    if len(message) < 5:
        errors.append("Please describe your query.")
    if errors:
        return render_support(errors, "query", 400)
    if not is_bot():
        db.session.add(Query(name=name, phone=phone, email=email, message=message, service=field("service"), consent=True))
        db.session.commit()
        notify("New website query", [f"Name: {name}", f"Phone: {phone}", f"Email: {email}", f"Service: {field('service')}", "", message])
    flash("Thank you. Your query has been received and the office will contact you.", "success")
    return redirect(url_for("public.support") + "#query")


@bp.route("/support/appointment", methods=["POST"])
@limiter.limit("5 per minute; 30 per hour")
def submit_appointment():
    errors = []
    name, phone, email, message = validate_contact("appointment", errors)
    preferred = None
    try:
        preferred = datetime.strptime(field("preferred_date", 10), "%Y-%m-%d").date()
        if preferred < date.today():
            errors.append("Please choose a future date for the appointment.")
    except ValueError:
        errors.append("Please choose a preferred date.")
    if errors:
        return render_support(errors, "appointment", 400)
    if not is_bot():
        db.session.add(Appointment(name=name, phone=phone, email=email, message=message, service=field("service"),
                                   preferred_date=preferred, preferred_time=field("preferred_time", 40), consent=True))
        db.session.commit()
        notify("New appointment request", [f"Name: {name}", f"Phone: {phone}", f"Email: {email}",
                                           f"Preferred: {preferred} {field('preferred_time', 40)}", "", message])
    flash("Thank you. Your appointment request has been received; the office will confirm the time.", "success")
    return redirect(url_for("public.support") + "#appointment")


def render_careers(errors=None, status=200):
    return render_template(
        "careers.html", page=get_page("careers"), errors=errors or [], form=request.form,
        openings=Opening.query.filter_by(is_open=True).order_by(Opening.created_at.desc()).all(),
        captcha=new_captcha("career"),
    ), status


@bp.route("/careers")
def careers():
    return render_careers()


@bp.route("/careers/apply", methods=["POST"])
@limiter.limit("5 per minute; 20 per hour")
def apply():
    errors = []
    name, phone, email, message = validate_contact("career", errors)
    resume_file = request.files.get("resume")
    if not resume_file or not resume_file.filename:
        errors.append("Please attach your resume as a PDF.")
    if errors:
        return render_careers(errors, 400)
    if not is_bot():
        try:
            resume = save_upload(resume_file, "resumes")
        except UploadError as exc:
            return render_careers([f"Resume: {exc}"], 400)
        db.session.add(Application(name=name, phone=phone, email=email, message=message,
                                   position=field("position"), resume=resume, consent=True))
        db.session.commit()
        notify("New career application", [f"Name: {name}", f"Phone: {phone}", f"Email: {email}", f"Position: {field('position')}"])
    flash("Thank you. Your application has been received.", "success")
    return redirect(url_for("public.careers") + "#apply")


@bp.route("/contact")
def contact():
    return render_template("contact.html", page=get_page("contact"))


@bp.route("/disclaimer")
def disclaimer():
    return render_template("page.html", page=get_page("disclaimer"))


@bp.route("/privacy-policy")
def privacy():
    return render_template("page.html", page=get_page("privacy"))


@bp.route("/terms")
def terms():
    return render_template("page.html", page=get_page("terms"))


# ---------------------------------------------------------------- media & SEO
@bp.route("/media/<kind>/<name>")
def media(kind, name):
    if kind not in PUBLIC_KINDS:
        abort(404)
    download_name = None
    if kind == "documents":
        doc = Download.query.filter_by(filename=name).first_or_404()
        download_name = re.sub(r"[^A-Za-z0-9 _-]+", "", doc.title).strip() or "document"
        download_name += "." + name.rsplit(".", 1)[-1]
    return send_from_directory(upload_dir(kind), name, as_attachment=kind == "documents",
                               download_name=download_name, max_age=3600)


def site_url():
    return current_app.config["SITE_URL"] or request.url_root.rstrip("/")


@bp.route("/sitemap.xml")
def sitemap():
    paths = [url_for(f"public.{e}") for e in ("home", "about", "services", "knowledge", "support", "careers",
                                              "contact", "disclaimer", "privacy", "terms")]
    paths += [url_for("public.service_detail", slug=s.slug) for s in Service.query.filter_by(is_visible=True)]
    paths += [url_for("public.article", slug=a.slug) for a in Article.query.filter_by(is_published=True)]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml += [f"  <url><loc>{site_url()}{p}</loc></url>" for p in paths]
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


@bp.route("/robots.txt")
def robots():
    return Response(f"User-agent: *\nDisallow: /admin/\nSitemap: {site_url()}/sitemap.xml\n", mimetype="text/plain")
