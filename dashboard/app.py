from flask import (
    Flask,
    render_template,
    redirect,
    request,
    send_from_directory
)

from flask import session
from werkzeug.utils import secure_filename

import json
import os
from supabase import create_client


SUPABASE_URL = "https://mztdxodzbwbgtwbelltc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im16dGR4b2R6YndiZ3R3YmVsbHRjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc3NTcxMjEsImV4cCI6MjA5MzMzMzEyMX0.gEBgtPsjRxipjBCB_dTt05hFGZ2xGh4lJhJH5TkUVNA"

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# =========================
# FLASK
# =========================

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates"
)

app.secret_key = "social_ai_secret"

# =========================
# UPLOADS
# =========================

UPLOAD_FOLDER = "uploads"

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

app.config[
    "UPLOAD_FOLDER"
] = UPLOAD_FOLDER

# =========================
# HOME
# =========================

@app.route("/")
def home():

    if "user" not in session:
        return redirect("/login")
        
resposta = supabase.table(
    "posts"
).select("*").eq(
    "email",
    session["user"]
).execute()

agendamentos = resposta.data

    posts_ordenados = sorted(
        agendamentos,
        key=lambda x: (
            x["data"],
            x["hora"]
        )
    )

    return render_template(
        "index.html",
        posts=posts_ordenados
    )

# =========================
# AGENDAMENTOS
# =========================

@app.route("/agendamentos")
def agendamentos():

    with open(
        "scheduler/agendamentos.json",
        "r",
        encoding="utf-8"
    ) as file:

        posts = json.load(file)

    return render_template(
        "index.html",
        posts=posts
    )

# =========================
# PUBLICAÇÕES
# =========================

@app.route("/publicacoes")
def publicacoes():

    with open(
        "scheduler/agendamentos.json",
        "r",
        encoding="utf-8"
    ) as file:

resposta = supabase.table(
    "posts"
).select("*").eq(
    "email",
    session["user"]
).execute()

posts = resposta.data


    posts_publicados = [
        post
        for post in posts
        if post["status"] == "executado"
    ]

    return render_template(
        "index.html",
        posts=posts_publicados
    )

# =========================
# IA
# =========================

@app.route("/ia")
def ia():

    return render_template(
        "index.html",
        posts=[]
    )

# =========================
# CONFIGURAÇÕES
# =========================

@app.route("/configuracoes")
def configuracoes():

    return render_template(
        "index.html",
        posts=[]
    )

# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        senha = request.form["senha"]

        try:

            resposta = supabase.auth.sign_in_with_password({
                "email": email,
                "password": senha
            })

            session["user"] = email

            return redirect("/")

        except Exception:

            return render_template(
                "login.html",
                erro="E-mail ou senha inválidos"
            )

    return render_template(
        "login.html"
    )

# =========================
# REGISTER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]

        try:

            supabase.auth.sign_up({
                "email": email,
                "password": senha
            })

            return render_template(
                "register.html",
                sucesso="Conta criada com sucesso"
            )

        except Exception:

            return render_template(
                "register.html",
                erro="Erro ao criar conta"
            )

    return render_template(
        "register.html"
    )

# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")

# =========================
# PUBLICAR
# =========================

@app.route("/publicar/<int:post_id>")
def publicar(post_id):

    resposta = supabase.table(
        "posts"
    ).select("*").eq(
        "id",
        post_id
    ).execute()

    post = resposta.data[0]

    # =========================
    # LINKEDIN
    # =========================

    if post["rede"] == "linkedin":

        os.system(
            "python linkedin/postar.py"
        )

    # =========================
    # INSTAGRAM
    # =========================

    if post["rede"] == "instagram":

        print("Instagram futuramente")

    # =========================
    # ALTERAR STATUS
    # =========================

    supabase.table(
        "posts"
    ).update({
        "status":"executado"
    }).eq(
        "id",
        post_id
    ).execute()

    return redirect("/")

# =========================
# EXCLUIR
# =========================

supabase.table(
    "posts"
).delete().eq(
    "id",
    post_id
).execute()

return redirect("/")

# =========================
# UPLOAD
# =========================

@app.route("/upload/<int:post_id>", methods=["POST"])
def upload(post_id):

    if "imagem" not in request.files:
        return "Nenhum arquivo enviado"

    arquivo = request.files["imagem"]

    if arquivo.filename == "":
        return "Arquivo inválido"

    nome_arquivo = secure_filename(
        arquivo.filename
    )

    conteudo = arquivo.read()

    supabase.storage.from_("social-ai").upload(
        nome_arquivo,
        conteudo,
        {
            "content-type": arquivo.content_type
        }
    )

    imagem_url = f"{SUPABASE_URL}/storage/v1/object/public/social-ai/{nome_arquivo}"

    with open(
        "scheduler/agendamentos.json",
        "r",
        encoding="utf-8"
    ) as file:

        posts = json.load(file)

    posts[post_id]["imagem"] = imagem_url

    with open(
        "scheduler/agendamentos.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            posts,
            file,
            indent=4,
            ensure_ascii=False
        )

    return redirect("/")

# =========================
# START
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
