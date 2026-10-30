"""Serve the dashboard and investigation lab together, sharing loaded models."""

from werkzeug.middleware.dispatcher import DispatcherMiddleware

from src.app.app import app
from src.investigation.app import app as lab

app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/lab": lab})
