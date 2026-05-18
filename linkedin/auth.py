import webbrowser
import os
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv(
    "LINKEDIN_CLIENT_ID"
)

REDIRECT_URI = os.getenv(
    "LINKEDIN_REDIRECT_URI"
)

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

print("Abrindo navegador LinkedIn 🚀")

webbrowser.open(auth_url)
