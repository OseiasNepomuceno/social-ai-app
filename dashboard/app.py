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
import mercadopago
from supabase import create_client

# =========================
# SUPABASE (ENV VARS SEGURAS)
# =========================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MERCADO_PAGO_TOKEN = os.getenv("MERCADO_PAGO_TOKEN")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Variáveis do Supabase não configuradas")

if not MERCADO_PAGO_TOKEN:
    print("⚠️ Mercado Pago não configurado")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
mp = mercadopago.SDK(MERCADO_PAGO_TOKEN) if MERCADO_PAGO_TOKEN else None

print("SUPABASE OK:", bool(SUPABASE_URL and SUPABASE_KEY))
print("MERCADO PAGO OK:", bool(MERCADO_PAGO_TOKEN))


# =========================
# FUNÇÃO: LIMITES DO PLANO
# =========================

def verificar_limite(user_id):

    res = supabase.table("users").select("*").eq("id", user_id).execute()

    if not res.data:
        return False, "Usuário não encontrado"

    user = res.data[0]

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

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# =========================
# HOME
# =========================

@app.route("/")
def home():

    if "user" not in session:
        return redirect("/login")

    user_id = session["user"]

    resposta = supabase.table("posts") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute()

    posts = resposta.data

    posts_ordenados = sorted(
        posts,
        key=lambda x: (x.get("data", ""), x.get("hora", ""))
    )

    return render_template("index.html", posts=posts_ordenados)


# =========================
# AGENDAMENTOS
# =========================

@app.route("/agendamentos")
def agendamentos():

    if "user" not in session:
        return redirect("/login")

    user_id = session["user"]

    resposta = supabase.table("posts") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute()

    return render_template("index.html", posts=resposta.data)


# =========================
# PUBLICAÇÕES
# =========================

@app.route("/publicacoes")
def publicacoes():

    if "user" not in session:
        return redirect("/login")

    user_id = session["user"]

    resposta = supabase.table("posts") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute()

    posts_publicados = [
        p for p in resposta.data
        if p.get("status") == "executado"
    ]

    return render_template("index.html", posts=posts_publicados)


# =========================
# IA
# =========================

@app.route("/ia")
def ia():

    if "user" not in session:
        return redirect("/login")

    return render_template("index.html", posts=[])


# =========================
# CONFIGURAÇÕES
# =========================

@app.route("/configuracoes")
def configuracoes():

    if "user" not in session:
        return redirect("/login")

    return render_template("index.html", posts=[])


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

            user = resposta.user

            session["user"] = user.id
            session["email"] = user.email

            # cria usuário se não existir (SaaS base)
            supabase.table("users").upsert({
                "id": user.id,
                "email": user.email,
                "plano": "gratuito",
                "posts_limite": 10,
                "posts_usados": 0
            }).execute()

            return redirect("/")

        except Exception as e:
            print("LOGIN ERROR:", str(e))
            return render_template("login.html", erro="E-mail ou senha inválidos")

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

            return render_template("register.html", sucesso="Conta criada com sucesso")

        except Exception as e:
            print("REGISTER ERROR:", str(e))
            return render_template("register.html", erro="Erro ao criar conta")

    return render_template("register.html")


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =========================
# PUBLICAR (COM BLOQUEIO SAAS)
# =========================

@app.route("/publicar/<int:post_id>")
def publicar(post_id):

    if "user" not in session:
        return redirect("/login")

    user_id = session["user"]

    permitido, msg = verificar_limite(user_id)

    if not permitido:
        return redirect("/planos")

    post = supabase.table("posts") \
        .select("*") \
        .eq("id", post_id) \
        .eq("user_id", user_id) \
        .execute()

    if not post.data:
        return "Acesso negado"

    post = post.data[0]

    if post["rede"] == "linkedin":
        os.system("python linkedin/postar.py")

    if post["rede"] == "instagram":
        print("Instagram futuramente")

    supabase.table("posts") \
        .update({"status": "executado"}) \
        .eq("id", post_id) \
        .eq("user_id", user_id) \
        .execute()

    # incrementa uso (seguro)
    usuario = supabase.table("users") \
        .select("*") \
        .eq("id", user_id) \
        .execute()

    if usuario.data:
        u = usuario.data[0]

        supabase.table("users") \
            .update({
                "posts_usados": u.get("posts_usados", 0) + 1
            }) \
            .eq("id", user_id) \
            .execute()

    return redirect("/")


# =========================
# EXCLUIR (MULTIUSUÁRIO)
# =========================

@app.route("/excluir/<int:post_id>")
def excluir(post_id):

    if "user" not in session:
        return redirect("/login")

    user_id = session["user"]

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

    user_id = session["user"]

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

    post = supabase.table("posts") \
        .select("*") \
        .eq("id", post_id) \
        .eq("user_id", user_id) \
        .execute()

    if not post.data:
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
