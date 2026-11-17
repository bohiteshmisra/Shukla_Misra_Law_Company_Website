"""Production server for Windows (and anywhere else): waitress serving the site.

    python run_server.py

Reads HOST and PORT from the environment or .env (defaults 127.0.0.1:8080).
Under IIS, web.config passes the port IIS assigned.
"""
import os
import sys
from pathlib import Path

from waitress import serve

from wsgi import app

if __name__ == "__main__":
    if not Path(app.config["DB_PATH"]).exists():
        sys.exit("Database not found. Run setup first:  flask --app wsgi init-db")
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8080"))
    print(f"Serving on http://{host}:{port}  (Ctrl+C to stop)")
    serve(app, host=host, port=port, threads=int(os.environ.get("THREADS", "8")), ident=None)
