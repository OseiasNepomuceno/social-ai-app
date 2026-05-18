import os
from urllib.parse import quote
from flask import redirect, session

# =========================
# ENV
# =========================

CLIENT_ID = os.getenv(
    "LINKEDIN_CLIENT_ID"
)

REDIRECT_URI = os.getenv(
    "LINKEDIN_REDIRECT_URI"
)

# =========================
# FUNÇÃO OAUTH
# =========================

def linkedin_auth():

    scope = quote(
        "openid profile email w_member_social"
    )

    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        "?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={scope}"
    )

    return redirect(auth_url)
