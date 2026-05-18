from flask import (
    Flask,
    render_template,
    redirect,
    request,
    send_from_directory,
    session
)

from werkzeug.utils import secure_filename
import json
import os
from supabase import create_client

import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def verificar_limite(user_id):

    usuario = supabase.table("users").select("*").eq("id", user_id).execute()

    if not usuario.data:
        return False, "Usuário não encontrado"

    user = usuario.data[0]

    plano = user.get("plano", "gratuito")
    limite = user.get("posts_limite", 10)
    usados = user.get("posts_usados", 0)

    if plano == "business":
        return True, "ok"

    if usados >= limite:
        return False, "Limite do plano atingido"

    return True, "ok"

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

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# =========================
# HOME
# =========================

@app.route("/")
def home():

    if "user" not in session:
        return redirect("/login")

    user_id = session["user"]
    
    resposta = supabase.table(
        "posts"
    ).select("*").eq(
        "email",
        session["user"]
    ).execute()

    agendamentos = resposta.data

    posts_ordenados = sorted(
        agendamentos,
        key=lambda x: (x["data"], x["hora"])
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

    if "user" not in session:
        return redirect("/login")

    user_id = session["user"]

    resposta = supabase.table(
        "posts"
    ).select("*").eq(
        "email",
        session["user"]
    ).execute()

    posts = resposta.data

    return render_template(
        "index.html",
        posts=posts
    )


# =========================
# PUBLICAÇÕES
# =========================

@app.route("/publicacoes")
def publicacoes():

    if "user" not in session:
        return redirect("/login")

    user_id = session["user"]

    resposta = supabase.table(
        "posts"
    ).select("*").eq(
        "email",
        session["user"]
    ).execute()

    posts = resposta.data

    posts_publicados = [
        post for post in posts
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

            # pega usuário logado corretamente
            user = resposta.user

            print("LOGIN OK:", user)

            # sessão
            session["user"] = user.id
            session["email"] = user.email

            # =========================
            # CRIAR USUÁRIO NO BANCO (SAAS)
            # =========================
            supabase.table("users").upsert({
                "id": user.id,
                "email": user.email,
                "plano": "gratuito",
                "posts_limite": 10,
                "posts_usados": 0
            }).execute()

            return redirect("/")

        except Exception as e:

            print("LOGIN ERROR REAL:", str(e))

            return render_template(
                "login.html",
                erro="E-mail ou senha inválidos"
            )

    return render_template("login.html")


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

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

    return render_template("register.html")


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =========================
# PUBLICAR (MULTIUSUÁRIO)
# =========================

@app.route("/publicar/<int:post_id>")
def publicar(post_id):

    if "user" not in session:
        return redirect("/login")

    user_id = session["user"]  # 🔐 AQUI ENTRA O USER_ID

    resposta = supabase.table("posts") \
        .select("*") \
        .eq("id", post_id) \
        .eq("user_id", user_id) \
        .execute()

    if not resposta.data:
        return "Acesso negado"

    post = resposta.data[0]

    if post["rede"] == "linkedin":
        os.system("python linkedin/postar.py")

    if post["rede"] == "instagram":
        print("Instagram futuramente")

    supabase.table("posts") \
        .update({"status": "executado"}) \
        .eq("id", post_id) \
        .eq("user_id", user_id) \
        .execute()

    return redirect("/")


# =========================
# EXCLUIR (MULTIUSUÁRIO)
# =========================

@app.route("/excluir/<int:post_id>")
def excluir(post_id):

    if "user" not in session:
        return redirect("/login")

    user_id = session["user"]  # 🔐 AQUI ENTRA O USER_ID

    supabase.table("posts") \
        .delete() \
        .eq("id", post_id) \
        .eq("user_id", user_id) \
        .execute()

    return redirect("/")


# =========================
# UPLOAD (MULTIUSUÁRIO)
# =========================

@app.route("/upload/<int:post_id>", methods=["POST"])
def upload(post_id):

    if "user" not in session:
        return redirect("/login")

    user_id = session["user"]  # 🔐 AQUI ENTRA O USER_ID

    if "imagem" not in request.files:
        return "Nenhum arquivo enviado"

    arquivo = request.files["imagem"]

    if arquivo.filename == "":
        return "Arquivo inválido"

    nome_arquivo = secure_filename(arquivo.filename)
    conteudo = arquivo.read()

    supabase.storage.from_("social-ai").upload(
        nome_arquivo,
        conteudo,
        {"content-type": arquivo.content_type}
    )

    imagem_url = f"{SUPABASE_URL}/storage/v1/object/public/social-ai/{nome_arquivo}"

    # 🔐 garante que só altera o próprio usuário
    resposta = supabase.table("posts") \
        .select("*") \
        .eq("id", post_id) \
        .eq("user_id", user_id) \
        .execute()

    if not resposta.data:
        return "Acesso negado"

    supabase.table("posts") \
        .update({"imagem": imagem_url}) \
        .eq("id", post_id) \
        .eq("user_id", user_id) \
        .execute()

    return redirect("/")
# =========================
# START
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
