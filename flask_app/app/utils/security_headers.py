"""Security headers applied to every response.

Tuned for this app: no third-party scripts, inline <style> only for the
branding custom properties, and images that may come from the storage CDN.
"""

from flask import current_app, request

CSP = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'self'; "
    "form-action 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "manifest-src 'self'; "
    "upgrade-insecure-requests"
)


def apply_security_headers(response):
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "SAMEORIGIN",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": (
            "geolocation=(), microphone=(), camera=(), interest-cohort=()"
        ),
        "Cross-Origin-Resource-Policy": "cross-origin",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Content-Security-Policy": CSP,
    }

    # Never let a browser or proxy cache authenticated pages.
    if request.path.startswith(("/dashboard", "/admin", "/auth", "/api")):
        headers["Cache-Control"] = "no-store"

    if request.is_secure and not current_app.debug and not current_app.testing:
        headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )

    for key, value in headers.items():
        response.headers.setdefault(key, value)
    return response
