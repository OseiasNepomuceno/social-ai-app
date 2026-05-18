import os
import requests

from flask import (
    request,
    session,
    redirect
)

from supabase import create_client

# =========================
# ENV
# =========================

CLIENT_ID = os.getenv(
    "LINKEDIN_CLIENT_ID"
)

CLIENT_SECRET = os.getenv(
    "LINKEDIN_CLIENT_SECRET"
)

REDIRECT_URI = os.getenv(
    "LINKEDIN_REDIRECT_URI"
)

SUPABASE_URL = os.getenv(
    "SUPABASE_URL"
)

SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY"
)

# =========================
# SUPABASE
# =========================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# =========================
# CALLBACK
# =========================

def linkedin_callback():

    # =========================
    # VALIDAR LOGIN
    # =========================

    if "user" not in session:

        return redirect("/login")

    user_id = session["user"]

    # =========================
    # CODE OAUTH
    # =========================

    code = request.args.get("code")

    if not code:

        return "❌ Código OAuth inválido"

    # =========================
    # TOKEN URL
    # =========================

    token_url = (
        "https://www.linkedin.com/oauth/v2/accessToken"
    )

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    # =========================
    # GERAR TOKEN
    # =========================

    response = requests.post(
        token_url,
        data=data
    )

    token_data = response.json()

    print("\n===== TOKEN DATA =====")

    print(token_data)

    access_token = token_data.get(
        "access_token"
    )

    if not access_token:

        return "❌ Erro ao conectar LinkedIn"

    # =========================
    # SALVAR TOKEN USER
    # =========================

    supabase.table("users").update({
        "linkedin_token": access_token
    }).eq(
        "id",
        user_id
    ).execute()

    print("✅ TOKEN LINKEDIN SALVO")

    return redirect("/")
