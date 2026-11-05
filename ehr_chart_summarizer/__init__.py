"""Agentic Longitudinal EHR Chart Summarizer built with Google ADK."""

import os
import ssl
import certifi

if not os.environ.get("SSL_CERT_FILE") and ssl.get_default_verify_paths().cafile is None:
    os.environ["SSL_CERT_FILE"] = certifi.where()
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

from . import agent

