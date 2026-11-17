import sqlite3

from app.extensions import db
from app.models import (Article, AuditLog, ComplianceDate, Download, Faq, Page, Query, Service, Setting, TeamMember,
                        User)
from conftest import NEW_PASSWORD, PDF, PNG, make_app, upload


def login(client, password, username="admin"):
    return client.post("/admin/login", data={"username": username, "password": password})


# ------------------------------------------------------------ authentication
def test_admin_requires_login(client):
    for path in ("/admin/", "/admin/content/services", "/admin/inbox/queries", "/admin/settings", "/admin/audit-log"):
        resp = client.get(path)
        assert resp.status_code == 302 and "/admin/login" in resp.headers["Location"]
    assert client.post("/admin/backup").status_code == 302


def test_first_login_forces_password_change(app, client):
    assert login(client, app.config["ADMIN_TEMP_PASSWORD"]).status_code == 302
    resp = client.get("/admin/")
    assert resp.status_code == 302 and "change-password" in resp.headers["Location"]

    weak = client.post("/admin/change-password", data={"current": app.config["ADMIN_TEMP_PASSWORD"], "new": "short1", "confirm": "short1"})
    assert weak.status_code == 400 and b"at least 10 characters" in weak.data

    ok = client.post("/admin/change-password", data={"current": app.config["ADMIN_TEMP_PASSWORD"], "new": NEW_PASSWORD, "confirm": NEW_PASSWORD})
    assert ok.status_code == 302
    assert client.get("/admin/").status_code == 200


def test_password_is_stored_hashed(app, admin):
    with app.app_context():
        stored = User.query.one().password_hash
    assert NEW_PASSWORD not in stored and stored.startswith(("scrypt:", "pbkdf2:"))


def test_wrong_password_and_lockout(app, client):
    for _ in range(5):
        assert login(client, "wrong-password").status_code == 401
    locked = login(client, app.config["ADMIN_TEMP_PASSWORD"])
    assert locked.status_code == 401 and b"temporarily locked" in locked.data
    with app.app_context():
        assert AuditLog.query.filter_by(action="lockout").count() == 1


def test_unknown_user_gets_same_message(client):
    resp = login(client, "whatever", username="nobody")
    assert resp.status_code == 401 and b"Incorrect username or password" in resp.data


def test_idle_session_is_signed_out(app, admin):
    with admin.session_transaction() as sess:
        sess["last_seen"] = 0
    resp = admin.get("/admin/")
    assert resp.status_code == 302 and "/admin/login" in resp.headers["Location"]
    assert admin.get("/admin/").status_code == 302


def test_logout(admin):
    assert admin.post("/admin/logout").status_code == 302
    assert admin.get("/admin/").status_code == 302


def test_login_is_rate_limited(tmp_path):
    client = make_app(tmp_path, RATELIMIT_ENABLED=True).test_client()
    codes = [login(client, "x", username="nobody").status_code for _ in range(12)]
    assert codes[-1] == 429


def test_open_redirect_is_ignored(app, client):
    resp = client.post("/admin/login?next=https://evil.example/", data={"username": "admin", "password": app.config["ADMIN_TEMP_PASSWORD"]})
    assert resp.headers["Location"] == "/admin/"


# ------------------------------------------------------------ content management
def test_every_admin_screen_loads(admin):
    paths = ["/admin/", "/admin/settings", "/admin/audit-log", "/admin/change-password"]
    for name in ("pages", "services", "team", "articles", "calendar", "downloads", "links", "faqs", "openings"):
        paths += [f"/admin/content/{name}"]
        if name != "pages":
            paths += [f"/admin/content/{name}/new"]
    paths += [f"/admin/inbox/{kind}" for kind in ("queries", "appointments", "applications")]
    paths += ["/admin/content/pages/1", "/admin/content/services/1", "/admin/content/faqs/1"]
    for path in paths:
        assert admin.get(path).status_code == 200, path


def test_edit_page_content_and_seo(app, admin, client):
    with app.app_context():
        about = Page.query.filter_by(slug="about").one()
    resp = admin.post(f"/admin/content/pages/{about.id}", data={
        "title": "About Our Firm", "body_html": "<p>Updated <strong>profile</strong> text.</p>",
        "meta_title": "Custom SEO title", "meta_description": "Custom description"})
    assert resp.status_code == 302
    html = client.get("/about").get_data(as_text=True)
    assert "About Our Firm" in html and "Updated <strong>profile</strong> text." in html
    assert "<title>Custom SEO title</title>" in html and 'content="Custom description"' in html


def test_pages_cannot_be_created_or_deleted(admin):
    assert admin.get("/admin/content/pages/new").status_code == 404
    assert admin.post("/admin/content/pages/1/delete").status_code == 404


def test_rich_text_is_sanitised(app, admin, client):
    admin.post("/admin/content/pages/2", data={
        "title": "About", "body_html": '<p onclick="steal()">Hi</p><script>alert(1)</script><a href="javascript:alert(1)">x</a><img src=x onerror=alert(1)>'})
    html = client.get("/about").get_data(as_text=True)
    for bad in ("<script>alert", "onclick", "javascript:", "onerror"):
        assert bad not in html
    assert "<p>Hi</p>" in html


def test_service_create_reorder_hide_delete(app, admin, client):
    resp = admin.post("/admin/content/services/new", data={
        "title": "Forensic Accounting", "slug": "", "summary": "Investigation support.", "body_html": "<p>Scope.</p>", "is_visible": "1"})
    assert resp.status_code == 302
    with app.app_context():
        new = Service.query.filter_by(slug="forensic-accounting").one()
        assert new.sort_order == 11
        new_id = new.id
    assert client.get("/services/forensic-accounting").status_code == 200

    admin.post(f"/admin/content/services/{new_id}/move/up")
    with app.app_context():
        ordered = [s.slug for s in Service.query.order_by(Service.sort_order)]
    assert ordered.index("forensic-accounting") == 9

    admin.post(f"/admin/content/services/{new_id}", data={"title": "Forensic Accounting", "slug": "forensic-accounting", "body_html": "<p>Scope.</p>"})
    assert client.get("/services/forensic-accounting").status_code == 404  # unchecked "show on website"

    assert admin.post(f"/admin/content/services/{new_id}/delete").status_code == 302
    with app.app_context():
        assert Service.query.count() == 10


def test_duplicate_slug_gets_suffix_and_title_required(app, admin):
    admin.post("/admin/content/services/new", data={"title": "GST", "is_visible": "1"})
    with app.app_context():
        assert Service.query.filter_by(slug="gst-2").count() == 1
    resp = admin.post("/admin/content/services/new", data={"title": ""})
    assert resp.status_code == 400 and b"Title is required" in resp.data


def test_team_profile_with_photo(app, admin, client):
    data = {"name": "CA Example Partner", "designation": "Partner", "qualifications": "B.Com, FCA", "membership_no": "000000",
            "bio": "Profile text.", "is_partner": "1", "is_visible": "1", "image": upload(PNG, "photo.png")}
    assert admin.post("/admin/content/team/new", data=data, content_type="multipart/form-data").status_code == 302
    with app.app_context():
        member = TeamMember.query.one()
    assert client.get(f"/media/images/{member.image}").status_code == 200
    html = client.get("/about").get_data(as_text=True)
    assert "CA Example Partner" in html and "ICAI Membership No. 000000" in html

    bad = {"name": "Other", "image": upload(b"<html>not an image</html>", "x.png")}
    resp = admin.post("/admin/content/team/new", data=bad, content_type="multipart/form-data")
    assert resp.status_code == 400 and b"does not match its type" in resp.data


def test_article_calendar_faq_link_opening(app, admin, client):
    admin.post("/admin/content/articles/new", data={"title": "Advance tax reminder", "category": "update", "summary": "Note.",
                                                    "body_html": "<p>Body.</p>", "is_published": "1"})
    assert client.get("/knowledge/advance-tax-reminder").status_code == 200
    with app.app_context():
        article_id = Article.query.filter_by(slug="advance-tax-reminder").one().id
    admin.post(f"/admin/content/articles/{article_id}", data={"title": "Advance tax reminder", "slug": "advance-tax-reminder", "category": "update"})
    assert client.get("/knowledge/advance-tax-reminder").status_code == 404  # unpublished

    admin.post("/admin/content/calendar/new", data={"due_date": "2099-03-15", "title": "Advance tax instalment", "category": "Income Tax"})
    assert b"Advance tax instalment" in client.get("/knowledge").data
    bad = admin.post("/admin/content/calendar/new", data={"due_date": "", "title": "No date"})
    assert bad.status_code == 400

    admin.post("/admin/content/faqs/new", data={"question": "Is parking available?", "answer": "<p>Yes.</p>", "is_visible": "1"})
    assert b"Is parking available?" in client.get("/support").data

    assert admin.post("/admin/content/links/new", data={"title": "Bad", "url": "javascript:alert(1)"}).status_code == 400
    admin.post("/admin/content/links/new", data={"title": "RBI", "url": "https://www.rbi.org.in/"})
    assert b"https://www.rbi.org.in/" in client.get("/knowledge").data

    admin.post("/admin/content/openings/new", data={"title": "Articled Assistant", "kind": "Articleship", "location": "Lucknow",
                                                    "body_html": "<p>Details.</p>", "is_open": "1"})
    assert b"Articled Assistant" in client.get("/careers").data
    with app.app_context():
        assert ComplianceDate.query.filter_by(title="Advance tax instalment").count() == 1 and Faq.query.count() == 6


def test_download_upload_replace_and_delete(app, admin, client):
    data = {"title": "ITR checklist", "category": "Checklists", "filename": upload(PDF, "list.pdf")}
    assert admin.post("/admin/content/downloads/new", data=data, content_type="multipart/form-data").status_code == 302
    with app.app_context():
        doc = Download.query.one()
        doc_id, stored = doc.id, doc.filename
    resp = client.get(f"/media/documents/{stored}")
    assert resp.status_code == 200 and "attachment" in resp.headers["Content-Disposition"]
    assert b"ITR checklist" in client.get("/knowledge").data

    missing = admin.post("/admin/content/downloads/new", data={"title": "No file"}, content_type="multipart/form-data")
    assert missing.status_code == 400
    wrong = admin.post("/admin/content/downloads/new", data={"title": "Script", "filename": upload(b"MZ", "run.exe")}, content_type="multipart/form-data")
    assert wrong.status_code == 400

    admin.post(f"/admin/content/downloads/{doc_id}/delete")
    assert client.get(f"/media/documents/{stored}").status_code == 404


# ------------------------------------------------------------ inbox, settings, audit, backup
def seed_query(app, message="Please call me"):
    with app.app_context():
        db.session.add(Query(name="=cmd|calc", phone="9999999999", email="a@example.com", message=message, consent=True))
        db.session.commit()
        return Query.query.one().id


def test_inbox_handle_export_delete(app, admin):
    query_id = seed_query(app)
    assert b"Please call me" in admin.get("/admin/inbox/queries").data
    assert b"<strong>1</strong>" in admin.get("/admin/").data

    admin.post(f"/admin/inbox/queries/{query_id}/handled")
    with app.app_context():
        assert db.session.get(Query, query_id).handled

    export = admin.get("/admin/inbox/queries/export.csv")
    text = export.get_data(as_text=True)
    assert export.mimetype == "text/csv" and "Please call me" in text
    assert "'=cmd|calc" in text  # spreadsheet formula neutralised

    admin.post(f"/admin/inbox/queries/{query_id}/delete")
    with app.app_context():
        assert Query.query.count() == 0


def test_settings_update_shows_on_site(app, admin, client):
    with app.app_context():
        data = {s.key: s.value for s in Setting.query.all()}
    data.update(phone="+91 522 000 0000", email="office@example.com", whatsapp="+91 90000 00000", frn="012345C")
    assert admin.post("/admin/settings", data=data).status_code == 302
    html = client.get("/contact").get_data(as_text=True)
    assert "+91 522 000 0000" in html and "mailto:office@example.com" in html and "wa.me/919000000000" in html
    assert "Firm Registration No. 012345C" in html

    data["map_embed_url"] = "https://evil.example/frame"
    assert admin.post("/admin/settings", data=data).status_code == 400


def test_audit_log_records_changes(app, admin):
    admin.post("/admin/content/faqs/new", data={"question": "Audit me?", "is_visible": "1"})
    page = admin.get("/admin/audit-log").get_data(as_text=True)
    assert "created" in page and "FAQ: Audit me?" in page and "password changed" in page and "login" in page


def test_backup_is_a_valid_database(app, admin, tmp_path):
    resp = admin.post("/admin/backup")
    assert resp.status_code == 200 and "attachment" in resp.headers["Content-Disposition"]
    target = tmp_path / "restored.db"
    target.write_bytes(resp.data)
    con = sqlite3.connect(target)
    try:
        assert con.execute("select count(*) from service").fetchone()[0] == 10
        assert con.execute("pragma integrity_check").fetchone()[0] == "ok"
    finally:
        con.close()


def test_admin_pages_are_not_cached(admin):
    assert admin.get("/admin/").headers["Cache-Control"] == "no-store"
