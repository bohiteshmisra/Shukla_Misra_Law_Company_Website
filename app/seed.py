"""Starter content loaded by `flask init-db`. Everything here is editable in the admin panel.

Content follows ICAI website guidelines: informational only, no superlatives,
no client names, no fees.
"""
import secrets
from datetime import date

from werkzeug.security import generate_password_hash

from .extensions import db
from .models import Article, ComplianceDate, Faq, Page, Service, Setting, UsefulLink, User

SETTINGS = {
    "firm_name": "Shukla Mishra & Co",
    "tagline": "Chartered Accountants",
    "address": "MMIG-C2, Tedhi Pulia, Sector D, Aliganj",
    "city": "Lucknow",
    "state": "Uttar Pradesh",
    "pincode": "226021",
    "phone": "+91 522 402 8486",
    "whatsapp": "",
    "email": "",
    "hours": "Monday to Saturday, 11:00 AM – 7:00 PM",
    "frn": "",
    "established": "",
    "map_embed_url": "https://www.google.com/maps?q=Shukla+Mishra+%26+Co,+Tedhi+Pulia,+Aliganj,+Lucknow+226021&output=embed",
    "linkedin": "",
    "disclaimer_popup": (
        "As per the guidelines of the Institute of Chartered Accountants of India (ICAI), a Chartered "
        "Accountant firm is not permitted to solicit work or advertise. By clicking “I Agree”, you "
        "acknowledge that you are seeking information about Shukla Mishra & Co of your own accord, that "
        "there has been no advertisement, personal communication, solicitation or inducement of any sort "
        "from the firm or its members, and that the information on this website is provided only for "
        "general information and does not constitute professional advice."
    ),
}

PAGES = [
    ("home", "Chartered Accountants in Lucknow",
     "<p>Shukla Mishra &amp; Co is a firm of Chartered Accountants based in Aliganj, Lucknow. The firm "
     "provides audit and assurance, direct and indirect taxation, corporate compliance, accounting and "
     "advisory services to individuals, businesses, companies, trusts and non-resident Indians.</p>",
     "Shukla Mishra & Co | Chartered Accountants, Aliganj, Lucknow",
     "Shukla Mishra & Co, Chartered Accountants in Aliganj, Lucknow: audit, income tax, GST, company law, accounting and advisory services."),
    ("about", "About the Firm",
     "<p>Shukla Mishra &amp; Co is a Chartered Accountancy firm with its office at Tedhi Pulia, Aliganj, "
     "Lucknow, Uttar Pradesh. The firm works with proprietors, partnership firms, companies, LLPs, trusts, "
     "societies and individuals on audit, taxation, regulatory compliance and financial advisory matters.</p>"
     "<h2>Our approach</h2>"
     "<ul><li><strong>Integrity:</strong> work is carried out in accordance with the Code of Ethics and "
     "standards issued by the Institute of Chartered Accountants of India.</li>"
     "<li><strong>Confidentiality:</strong> client information is kept confidential and used only for the "
     "engagement for which it was shared.</li>"
     "<li><strong>Timeliness:</strong> statutory due dates are tracked so that filings are completed on time.</li>"
     "<li><strong>Clarity:</strong> matters are explained in plain language so that clients can take informed decisions.</li></ul>",
     "About Shukla Mishra & Co | Chartered Accountants, Lucknow",
     "Profile of Shukla Mishra & Co, Chartered Accountants, Aliganj, Lucknow: the firm, its approach and its partners."),
    ("services", "Services",
     "<p>The firm provides the following professional services. Select a service to read more about its scope.</p>",
     "Services | Shukla Mishra & Co, Chartered Accountants",
     "Audit and assurance, income tax, GST, company and LLP compliance, accounting, registrations, advisory and NRI taxation services."),
    ("knowledge", "Knowledge Centre",
     "<p>Articles, compliance due dates, useful links and downloadable checklists for general reference.</p>",
     "Knowledge Centre | Shukla Mishra & Co", "Articles, tax and compliance calendar, useful government links and downloads."),
    ("support", "Support",
     "<p>Find answers to common questions, send us a query or request an appointment. We respond during office hours.</p>",
     "Support | Shukla Mishra & Co", "Frequently asked questions, query form and appointment request."),
    ("careers", "Careers",
     "<p>The firm offers articleship training to CA students registered with ICAI and, from time to time, "
     "staff positions in audit, taxation and accounts. Current openings are listed below.</p>",
     "Careers | Shukla Mishra & Co", "Articleship and staff openings at Shukla Mishra & Co, Chartered Accountants, Lucknow."),
    ("contact", "Contact Us",
     "<p>You may visit, call or write to the office during working hours.</p>",
     "Contact | Shukla Mishra & Co, Aliganj, Lucknow", "Office address, phone, hours and location map of Shukla Mishra & Co, Aliganj, Lucknow."),
    ("disclaimer", "Disclaimer",
     "<p>This website is intended only to provide general information about Shukla Mishra &amp; Co and its "
     "services. It is not an advertisement and is not intended to solicit work in any manner.</p>"
     "<p>The contents of this website are for general information and do not constitute professional advice. "
     "Laws, rules and due dates change frequently; readers should obtain specific professional advice before "
     "acting on any information given here. The firm accepts no liability for any loss arising from reliance "
     "on the contents of this website.</p>"
     "<p>Links to external websites are provided for convenience only. The firm is not responsible for the "
     "content of those websites.</p>", "Disclaimer | Shukla Mishra & Co", ""),
    ("privacy", "Privacy Policy",
     "<p>This policy explains how Shukla Mishra &amp; Co handles personal data submitted through this website, "
     "in line with the Digital Personal Data Protection Act, 2023.</p>"
     "<h2>What we collect</h2><p>Name, phone number, email address and the details you enter in the query, "
     "appointment or career application forms, including any resume you upload.</p>"
     "<h2>Why we collect it</h2><p>Only to respond to your query, schedule the appointment you asked for, or "
     "consider your application. We do not use it for marketing and do not sell or share it with third "
     "parties, except where required by law.</p>"
     "<h2>Consent</h2><p>Each form asks for your consent before submission. You may withdraw consent at any time "
     "by contacting the office.</p>"
     "<h2>Retention and your rights</h2><p>Data is retained only as long as needed for the purpose for which it was "
     "given. You may ask for access to, correction of, or erasure of your personal data by contacting the "
     "office using the details on the Contact page.</p>"
     "<h2>Cookies</h2><p>This website uses only a session cookie needed for forms and security. It does not use "
     "advertising or tracking cookies.</p>", "Privacy Policy | Shukla Mishra & Co", ""),
    ("terms", "Terms of Use",
     "<p>By using this website you agree that its content is for general information only, that no "
     "client relationship is created by viewing it or by submitting a form, and that the content may be "
     "changed without notice.</p>"
     "<p>The content of this website is the property of Shukla Mishra &amp; Co and may not be reproduced "
     "without permission. These terms are governed by the laws of India and subject to the jurisdiction of "
     "the courts at Lucknow.</p>", "Terms of Use | Shukla Mishra & Co", ""),
]


def _svc(intro, items, closing=""):
    html = f"<p>{intro}</p><h2>Scope of services</h2><ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"
    return html + (f"<p>{closing}</p>" if closing else "")


SERVICES = [
    ("Audit & Assurance", "Statutory, tax, internal, stock and bank audits carried out as per applicable standards.",
     _svc("An audit gives owners, lenders and regulators an independent view of the financial statements and "
          "the controls behind them. Audits are conducted in accordance with the Standards on Auditing issued by ICAI.",
          ["Statutory audit of companies under the Companies Act, 2013",
           "Tax audit under the Income-tax law",
           "Internal audit and review of internal financial controls",
           "Stock and receivables audit for lenders",
           "Bank audits: statutory branch audit, concurrent audit and revenue audit",
           "Audit of trusts, societies, educational institutions and NGOs",
           "Agreed-upon procedures and special purpose reports"])),
    ("Income Tax", "Return filing, tax planning, TDS/TCS compliance, assessments and appeals.",
     _svc("Income tax services cover compliance through the year as well as representation before the tax authorities.",
          ["Preparation and filing of income tax returns for individuals, HUFs, firms, companies, LLPs and trusts",
           "Tax planning within the framework of the law and advance tax computation",
           "TDS and TCS: deduction advice, periodic statements and certificates",
           "Replies to notices, rectification requests and faceless assessment proceedings",
           "Appeals before the appellate authorities",
           "Capital gains computation on property, shares and other assets",
           "PAN, TAN and lower deduction certificate applications"],
          "Provisions, forms and due dates are revised from time to time; advice is given on the law applicable to the relevant year.")),
    ("GST", "Registration, returns, annual return and reconciliation, refunds, notices and GST audit.",
     _svc("Goods and Services Tax compliance involves periodic returns, reconciliation of input tax credit and "
          "timely response to departmental communication.",
          ["GST registration, amendment and cancellation",
           "Monthly and quarterly returns, including GSTR-1 and GSTR-3B",
           "Annual return and reconciliation statement",
           "Input tax credit reconciliation with supplier data",
           "Refund applications for exports and inverted duty structure",
           "Replies to notices, departmental audit support and appeals",
           "E-way bill and e-invoicing guidance",
           "Advisory on classification, rate and place of supply"])),
    ("Company & LLP Services", "Incorporation, ROC/MCA compliance and secretarial support for companies and LLPs.",
     _svc("From formation to annual filings, companies and LLPs must meet requirements of the Ministry of Corporate Affairs.",
          ["Incorporation of private limited companies, one person companies, Section 8 companies and LLPs",
           "Director Identification Number and digital signature assistance",
           "Annual filings of financial statements and annual return with the Registrar of Companies",
           "Changes in directors, registered office, capital and object clauses",
           "Maintenance of statutory registers and minutes",
           "Conversion, strike-off and closure procedures"])),
    ("Accounting, Bookkeeping & Payroll", "Books of account, financial statements and payroll compliance including PF and ESI.",
     _svc("Accurate books are the basis for every tax return, loan application and business decision.",
          ["Bookkeeping on Tally and other accounting software",
           "Preparation of financial statements and management reports",
           "Bank, debtor and creditor reconciliations",
           "Payroll processing and salary structuring",
           "Provident Fund, ESI and professional tax registrations and returns",
           "Fixed asset registers and inventory records"])),
    ("Business Registrations", "MSME/Udyam, Startup India, IEC, trademark and 12A/80G registrations.",
     _svc("New and growing organisations need a number of registrations before they can operate, trade or receive donations.",
          ["Udyam (MSME) registration",
           "Startup India recognition",
           "Import Export Code (IEC)",
           "Trademark application filing assistance",
           "Registration of trusts and societies, and 12A / 80G applications",
           "Shops and establishment and other local registrations",
           "FSSAI and other sector-specific licences"])),
    ("Business Advisory", "Business setup, project reports and CMA data, loan documentation, valuation and due diligence.",
     _svc("Advisory work supports decisions on starting, financing, expanding or restructuring a business.",
          ["Choice of business structure and setup advice",
           "Project reports and CMA data for bank finance",
           "Assistance with term loan and working capital proposals",
           "Business and share valuation",
           "Financial and tax due diligence",
           "Budgeting, cash flow forecasting and cost review"])),
    ("NRI & International Taxation", "FEMA, DTAA relief, remittance certificates and tax matters of non-residents.",
     _svc("Non-resident Indians and businesses with cross-border transactions deal with both Indian tax law and "
          "exchange control regulations.",
          ["Residential status determination and return filing for NRIs",
           "Relief under Double Taxation Avoidance Agreements",
           "Certificates for foreign remittances (Form 15CA / 15CB or the forms currently prescribed)",
           "Advice under FEMA on investment, repatriation and property transactions",
           "Lower or nil TDS certificates on sale of property by non-residents",
           "Advisory on NRE, NRO and FCNR accounts from a tax perspective"])),
    ("Certification & Attestation", "Certificates required by banks, government departments and other authorities.",
     _svc("Various authorities require certificates issued by a practising Chartered Accountant. Certificates are "
          "issued after verification of records and carry a UDIN as required by ICAI.",
          ["Net worth and turnover certificates",
           "Certificates for bank finance and stock statements",
           "Certificates under GST, Income-tax and FEMA",
           "Utilisation certificates for grants",
           "Certificates for tenders, visas and regulatory filings"])),
    ("Virtual CFO & Management Consultancy", "Ongoing finance function support, MIS and process review for businesses.",
     _svc("Businesses that do not need a full-time finance head can engage the firm for periodic finance and "
          "management support.",
          ["Monthly MIS and performance review",
           "Budgeting and variance analysis",
           "Working capital and cash flow management",
           "Design and review of internal processes and controls",
           "Coordination with bankers, auditors and investors",
           "Compliance calendar monitoring"])),
]

FAQS = [
    ("How can I engage the firm for a service?",
     "<p>You may call or visit the office during working hours, or use the query form on this page. "
     "A member of the firm will contact you to understand the requirement.</p>"),
    ("Which documents are generally needed for filing an income tax return?",
     "<p>Typically PAN, Aadhaar, Form 16 or salary details, bank statements, the annual information statement, "
     "details of investments and deductions, and details of any capital gains or other income. The exact list "
     "depends on your sources of income.</p>"),
    ("Do I need to visit the office in person?",
     "<p>Most compliance work can be handled by sharing documents electronically. An office meeting can be "
     "arranged through the appointment form where a discussion is needed.</p>"),
    ("How is the information I share kept confidential?",
     "<p>Client information is covered by the professional duty of confidentiality under the Chartered "
     "Accountants Act and the ICAI Code of Ethics, and is used only for the engagement concerned. "
     "See the Privacy Policy for details on website form data.</p>"),
    ("Does the firm take articled assistants?",
     "<p>Students registered with ICAI may check the Careers page for current openings and apply there.</p>"),
]

LINKS = [
    ("Income Tax e-Filing Portal", "https://www.incometax.gov.in/"),
    ("GST Portal", "https://www.gst.gov.in/"),
    ("Ministry of Corporate Affairs (MCA)", "https://www.mca.gov.in/"),
    ("Institute of Chartered Accountants of India (ICAI)", "https://www.icai.org/"),
    ("TRACES (TDS)", "https://www.tdscpc.gov.in/"),
    ("EPFO", "https://www.epfindia.gov.in/"),
    ("ESIC", "https://www.esic.gov.in/"),
    ("Udyam Registration", "https://udyamregistration.gov.in/"),
]

ARTICLES = [
    ("Documents to keep ready before filing your income tax return",
     "A general checklist of records that help in preparing an accurate return.",
     "<p>Collecting the right records before the return is prepared reduces errors and later notices. "
     "The following is a general checklist.</p><ul>"
     "<li>PAN and Aadhaar, and bank account details for refund</li>"
     "<li>Form 16 from the employer and salary slips</li>"
     "<li>Annual information statement and tax credit statement from the e-filing portal</li>"
     "<li>Interest certificates from banks and post office</li>"
     "<li>Proof of investments, insurance premiums, donations and loan interest claimed as deductions</li>"
     "<li>Sale and purchase documents for property, shares and mutual funds</li>"
     "<li>Rent receipts and rental income details</li></ul>"
     "<p>This note is for general information. The documents required depend on individual facts.</p>"),
    ("Information generally required for GST registration",
     "An outline of the details a business should arrange before applying for registration.",
     "<p>An application for GST registration is made online. Businesses are generally asked for the following.</p><ul>"
     "<li>PAN of the business or proprietor</li>"
     "<li>Aadhaar and photographs of the proprietor, partners or directors</li>"
     "<li>Proof of constitution, such as partnership deed or certificate of incorporation</li>"
     "<li>Proof of principal place of business, such as an electricity bill and rent agreement or ownership document</li>"
     "<li>Bank account details</li>"
     "<li>Authorisation in favour of the authorised signatory</li></ul>"
     "<p>Requirements may vary with the type of business and are revised from time to time.</p>"),
]

RECURRING_DATES = [
    (7, "Deposit of TDS / TCS for the previous month", "Income Tax"),
    (11, "GSTR-1 for the previous month (monthly filers)", "GST"),
    (15, "PF and ESI contribution for the previous month", "Payroll"),
    (20, "GSTR-3B for the previous month (monthly filers)", "GST"),
]


def set_temp_password(username="admin"):
    """Create the user if needed, set a random temporary password, force a change at login."""
    password = "Smc-" + secrets.token_urlsafe(9)
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username, password_hash="")
        db.session.add(user)
    user.password_hash = generate_password_hash(password)
    user.must_change_password = True
    user.failed_attempts = 0
    user.locked_until = None
    db.session.commit()
    return password


def seed_all(today=None):
    """Insert starter content where tables are empty. Returns the admin password if one was created."""
    from .security import slugify

    for key, value in SETTINGS.items():
        if not db.session.get(Setting, key):
            db.session.add(Setting(key=key, value=value))
    for slug, title, body, mt, md in PAGES:
        if not Page.query.filter_by(slug=slug).first():
            db.session.add(Page(slug=slug, title=title, body_html=body, meta_title=mt, meta_description=md))
    if not Service.query.first():
        for i, (title, summary, body) in enumerate(SERVICES, 1):
            db.session.add(Service(slug=slugify(title), title=title, summary=summary, body_html=body,
                                   sort_order=i, meta_title=f"{title} | Shukla Mishra & Co", meta_description=summary))
    if not Faq.query.first():
        for i, (q, a) in enumerate(FAQS, 1):
            db.session.add(Faq(question=q, answer=a, sort_order=i))
    if not UsefulLink.query.first():
        for i, (title, url) in enumerate(LINKS, 1):
            db.session.add(UsefulLink(title=title, url=url, sort_order=i))
    if not Article.query.first():
        for title, summary, body in ARTICLES:
            db.session.add(Article(slug=slugify(title), title=title, summary=summary, body_html=body,
                                   meta_title=title, meta_description=summary))
    if not ComplianceDate.query.first():
        today = today or date.today()
        for offset in range(3):
            month_index = today.month - 1 + offset
            year, month = today.year + month_index // 12, month_index % 12 + 1
            for day, title, category in RECURRING_DATES:
                db.session.add(ComplianceDate(due_date=date(year, month, day), title=title, category=category,
                                              description="Indicative date; confirm on the official portal."))
    db.session.commit()
    return None if User.query.first() else set_temp_password("admin")
