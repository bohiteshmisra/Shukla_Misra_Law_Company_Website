"""WSGI entry point: `flask --app wsgi ...` and any WSGI server use this."""
from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402  (environment must be loaded first)

app = create_app()
