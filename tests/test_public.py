import pytest

from app.extensions import db
from app.models import Application, Appointment, Query, Service
from conftest import PDF, captcha_answer, contact, make_app, upload

PAGES = ["/", "/about", "/services", "/knowledge", "/support", "/careers", "/contact",
         "/disclaimer", "/privacy-policy", "/terms"]


@pytest.mark.parametrize("path", PAGES)
def test_public_pages_load(client, path):
    resp = client.get(path)
    assert resp.status_code == 200
    assert b"Shukla Mishra &amp; Co" in resp.data


def test_home_shows_firm_details_and_disclaimer(client):
    html = client.get("/").get_data(as_text=True)
    assert "Tedhi Pulia" in html and "+91 522 402 8486" in html
    assert 'id="disclaimerModal"' in html and "I Agree" in html
    assert '"@type": "AccountingService"' in html
    assert "11:00 AM" in html


def test_all_ten_services_have_detail_pages(app, client):
    with app.app_context():
        slugs = [s.slug for s in Service.query.all()]
    assert len(slugs) == 10
    for slug in slugs:
        assert client.get(f"/services/{slug}").status_code == 200


def test_hidden_service_is_not_public(app, client):
    with app.app_context():
        service = Service.query.first()
        service.is_visible = False
        slug = service.slug
        db.session.commit()
    assert client.get(f"/services/{slug}").status_code == 404
    assert slug not in client.get("/sitemap.xml").get_data(as_text=True)


def test_no_icai_prohibited_wording(client):
    for path in PAGES:
        text = client.get(path).get_data(as_text=True).lower()
        for word in ("best ca", "leading firm", "testimonial", "no. 1", "our clients include"):
            assert word not in text


def test_security_headers(client):
    headers = client.get("/").headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "Referrer-Policy" in headers


def test_sitemap_robots_and_404(client):
    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200 and b"/services/gst" in sitemap.data
    assert b"Disallow: /admin/" in client.get("/robots.txt").data
    assert client.get("/no-such-page").status_code == 404


def test_query_is_stored(app, client):
    answer = captcha_answer(client, "/support", "query")
    resp = client.post("/support/query", data=contact(message="Need help with GST registration", service="GST", captcha=answer))
    assert resp.status_code == 302
    with app.app_context():
        saved = Query.query.one()
        assert saved.name == "Asha Verma" and saved.service == "GST" and saved.consent
    assert b"query has been received" in client.get("/support").data


def test_query_rejects_wrong_captcha_and_missing_consent(app, client):
    captcha_answer(client, "/support", "query")
    resp = client.post("/support/query", data=contact(message="A real question", captcha="999"))
    assert resp.status_code == 400 and b"verification question" in resp.data

    answer = captcha_answer(client, "/support", "query")
    data = contact(message="A real question", captcha=answer)
    del data["consent"]
    resp = client.post("/support/query", data=data)
    assert resp.status_code == 400 and b"consent" in resp.data
    with app.app_context():
        assert Query.query.count() == 0


def test_query_validates_email_and_phone(client):
    answer = captcha_answer(client, "/support", "query")
    resp = client.post("/support/query", data=contact(message="Hello there", email="not-an-email", phone="abc", captcha=answer))
    assert resp.status_code == 400
    assert b"valid email" in resp.data and b"valid phone" in resp.data


def test_captcha_cannot_be_reused(app, client):
    answer = captcha_answer(client, "/support", "query")
    assert client.post("/support/query", data=contact(message="First message", captcha=answer)).status_code == 302
    assert client.post("/support/query", data=contact(message="Second message", captcha=answer)).status_code == 400


def test_honeypot_submission_is_dropped(app, client):
    answer = captcha_answer(client, "/support", "query")
    resp = client.post("/support/query", data=contact(message="Buy cheap things", website="http://spam.example", captcha=answer))
    assert resp.status_code == 302
    with app.app_context():
        assert Query.query.count() == 0


def test_appointment_is_stored_and_past_date_rejected(app, client):
    answer = captcha_answer(client, "/support", "appointment")
    resp = client.post("/support/appointment", data=contact(preferred_date="2020-01-01", captcha=answer))
    assert resp.status_code == 400 and b"future date" in resp.data

    answer = captcha_answer(client, "/support", "appointment")
    resp = client.post("/support/appointment", data=contact(preferred_date="2099-01-05", preferred_time="Any time", captcha=answer))
    assert resp.status_code == 302
    with app.app_context():
        assert Appointment.query.one().preferred_date.year == 2099


def test_career_application_with_pdf(app, client):
    answer = captcha_answer(client, "/careers", "career")
    data = contact(position="General application", captcha=answer, resume=upload(PDF, "cv.pdf"))
    resp = client.post("/careers/apply", data=data, content_type="multipart/form-data")
    assert resp.status_code == 302
    with app.app_context():
        saved = Application.query.one()
        assert saved.resume.endswith(".pdf")
    # resumes are private: no public URL serves them
    assert client.get(f"/media/resumes/{saved.resume}").status_code == 404


@pytest.mark.parametrize("payload,name", [(b"MZ\x90\x00 not a pdf", "cv.pdf"), (PDF, "cv.exe"), (b"%PDF-" + b"0" * (2 * 1024 * 1024 + 10), "big.pdf")])
def test_career_application_rejects_bad_files(app, client, payload, name):
    answer = captcha_answer(client, "/careers", "career")
    data = contact(captcha=answer, resume=upload(payload, name))
    resp = client.post("/careers/apply", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400 and b"Resume:" in resp.data
    with app.app_context():
        assert Application.query.count() == 0


def test_csrf_token_is_required(tmp_path):
    client = make_app(tmp_path, WTF_CSRF_ENABLED=True).test_client()
    answer = captcha_answer(client, "/support", "query")
    resp = client.post("/support/query", data=contact(message="No token here", captcha=answer))
    assert resp.status_code == 400 and b"Session expired" in resp.data


def test_public_forms_are_rate_limited(tmp_path):
    client = make_app(tmp_path, RATELIMIT_ENABLED=True).test_client()
    codes = [client.post("/support/query", data={}).status_code for _ in range(7)]
    assert codes[:5] == [400] * 5 and codes[-1] == 429


def test_https_redirect_when_forced(tmp_path):
    client = make_app(tmp_path, FORCE_HTTPS=True).test_client()
    resp = client.get("/about")
    assert resp.status_code == 301 and resp.headers["Location"].startswith("https://")
    secure = client.get("/about", base_url="https://localhost")
    assert secure.status_code == 200 and "Strict-Transport-Security" in secure.headers
