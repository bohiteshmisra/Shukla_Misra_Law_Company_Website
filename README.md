# Shukla Mishra & Co — Website

Website for **Shukla Mishra & Co, Chartered Accountants** (MMIG-C2, Tedhi Pulia, Sector D, Aliganj,
Lucknow 226021) with an admin panel for updating all content.

- **Stack:** Python 3.10+ · Flask · SQLite (single file, no database server) · Bootstrap 5 · waitress
- **Runs on:** Windows 10/11 and Windows Server (also Linux/macOS)
- **No build step:** no Node.js needed; Bootstrap and the text editor are bundled in `app/static/vendor`

## What is included

| Public site | Admin panel (`/admin`) |
|---|---|
| Home, About, Contact (with map) | Username/password login, lockout after 5 failed attempts |
| 10 service pages (audit, income tax, GST, company/LLP, accounting & payroll, registrations, advisory, NRI taxation, certification, virtual CFO) | Edit text, image and SEO title/description of every page |
| Knowledge Centre: articles, compliance calendar, useful links, downloads | Add / edit / delete / reorder / hide services, FAQs, links |
| Support: FAQs, query form, appointment request | Partner and team profiles with photos |
| Careers: openings and application form with PDF resume | Articles, news updates, due dates, downloadable documents, openings |
| Disclaimer, Privacy Policy, Terms | Inbox for queries, appointments and applications, with CSV export |
| ICAI disclaimer pop-up, sitemap.xml, robots.txt | Firm details, audit log, one-click database backup, change password |

## 1. Run on Windows (local or server)

1. Install **Python 3.10 or newer** from <https://www.python.org/downloads/windows/>
   (tick *"Add python.exe to PATH"*).
2. Download or clone this repository, e.g. to `C:\inetpub\shuklamishra`.
3. Double-click **`scripts\setup.bat`** (or run it in Command Prompt). It creates a virtual
   environment, installs packages, creates the database with starter content and prints:

   ```
   Admin login created
     Username: admin
     Temporary password: Smc-xxxxxxxxxxxx
   ```

   Note the temporary password. It is shown only once.
4. Double-click **`scripts\run.bat`** and open <http://127.0.0.1:8080>.
5. Sign in at <http://127.0.0.1:8080/admin>. You are asked to set a new password
   (10+ characters, letters and numbers) before anything else.

Forgot the password or locked out? Run `scripts\reset-admin.bat` for a new temporary password.

### First things to do in the admin panel

- **Firm details:** add the email, WhatsApp number, Firm Registration Number and year of establishment
  (blank fields are simply not shown on the site).
- **Partners & Team:** add partner names, qualifications and ICAI membership numbers.
- **Services / Pages:** review the draft text of each page and adjust it to the firm's actual practice.
- **Compliance Calendar:** the starter dates are the usual monthly ones; add or correct as notified.

## 2. Settings (`.env`)

`setup.bat` copies `.env.example` to `.env`. Edit it in Notepad:

| Setting | Meaning |
|---|---|
| `SITE_URL` | Public address, e.g. `https://shuklamishra.com` (used in sitemap and canonical links) |
| `HOST`, `PORT` | Where `run.bat` listens. Use `HOST=0.0.0.0` to accept connections from other machines |
| `FORCE_HTTPS` | Set to `1` once HTTPS works: redirects to https and marks cookies Secure |
| `BEHIND_PROXY` | Set to `1` when running behind IIS or another reverse proxy |
| `MAIL_*` | SMTP details for email alerts on new queries, appointments and applications (optional) |
| `SMC_DATA_DIR` | Optional folder for the database and uploads (default: `instance\`) |

Restart the site after changing `.env`.

## 3. Deploy on IIS with HTTPS

1. **Enable IIS:** *Turn Windows features on or off* → Internet Information Services.
2. **Install HttpPlatformHandler** (Microsoft, free):
   <https://www.iis.net/downloads/microsoft/httpplatformhandler>
3. Put the site in `C:\inetpub\shuklamishra` and run `scripts\setup.bat` there.
   If you use another folder, edit the two paths in `web.config`.
4. Give the IIS application pool identity (`IIS AppPool\<pool name>`) **Modify** permission on the
   `instance` and `logs` folders, and Read on the rest.
5. In **IIS Manager** → *Sites* → *Add Website*: physical path `C:\inetpub\shuklamishra`,
   host name `shuklamishra.com` (add a second binding for `www.shuklamishra.com`).
6. Point the domain's DNS **A record** to the server's public IP address. (The domain currently
   points to Wix; change it at the domain registrar.)
7. **HTTPS certificate:** install a free Let's Encrypt certificate with
   [win-acme](https://www.win-acme.com/) (`wacs.exe`, choose the IIS site), or import a purchased
   certificate and add an `https` binding on port 443.
8. In `.env` set `SITE_URL=https://shuklamishra.com`, `BEHIND_PROXY=1`, `FORCE_HTTPS=1`,
   then restart the site in IIS Manager.

If the browser reports "too many redirects" after step 8, IIS is not passing the original scheme:
set `FORCE_HTTPS=0` and add an HTTP→HTTPS redirect rule in IIS instead.

**Without IIS:** set `HOST=0.0.0.0` and `PORT=80` in `.env` and start `scripts\run.bat` at boot with
Task Scheduler (*At startup*, *Run whether user is logged on or not*). Use this only on an internal
network or behind something that provides HTTPS.

## 4. Backups

- **Database:** Admin → Dashboard → *Download backup* (a consistent copy of `site.db`).
- **Uploaded files:** copy the `instance\uploads` folder.
- **Restore:** stop the site, replace `instance\site.db` with the backup, restore `uploads`, start the site.

## 5. Tests

```
scripts\test.bat
```

(or `pip install -r requirements-dev.txt` then `pytest -q`). The suite covers every public page,
all three forms, upload validation, CSRF, rate limiting, HTTPS redirect, login, lockout, forced
password change, idle sign-out, all content management screens, HTML sanitising, CSV export,
audit log and backup.

## 6. Security and compliance notes

- Passwords are stored hashed (scrypt). Login is rate limited; the account locks for 15 minutes after
  5 wrong attempts; the admin is signed out after 30 minutes of inactivity.
- All forms carry CSRF tokens. Public forms also have a verification question, a hidden spam trap and
  rate limits.
- Text entered in the editor is sanitised before it is saved. Uploads are checked by extension, size
  and file signature and stored under random names; resumes are never publicly reachable.
- Security headers (Content-Security-Policy, X-Frame-Options, nosniff, HSTS on HTTPS) are set on
  every response.
- **ICAI guidelines:** the starter content is informational only, with no superlatives, client names,
  testimonials or fees, and a disclaimer pop-up appears on first visit. Keep new content within the
  current ICAI website guidelines, and do not add logos other than the permitted "CA" logo.
- **DPDP Act:** every form asks for consent and links to the Privacy Policy. Delete enquiries from the
  inbox when they are no longer needed.
- Draft service text avoids rates, section numbers and specific deadlines because these change;
  please have a partner review it before going live.

## Project layout

```
app/
  __init__.py     app factory, security headers, CLI commands (init-db, reset-admin)
  models.py       database tables
  public.py       public pages and forms
  admin.py        admin panel
  security.py     sanitising, upload checks, verification question
  seed.py         starter content and firm details
  templates/      HTML templates (public and admin/)
  static/         CSS, JavaScript, bundled Bootstrap and Quill
tests/            automated tests
scripts/          setup.bat, run.bat, test.bat, reset-admin.bat
run_server.py     production server (waitress)
wsgi.py           WSGI entry point
web.config        IIS configuration
.env.example      settings template
```

Adding Hindi later: page text lives in the database and templates, so a second language can be added
as a parallel set of pages; this is not built yet.
