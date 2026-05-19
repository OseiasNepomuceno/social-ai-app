from flask import (
    Flask,
    render_template,
    redirect,
    request,
    session
)

from werkzeug.utils import secure_filename
import os
import json
import mercadopago
from dashboard.ia_engine import gerar_conteudo
from supabase import create_client
from linkedin.auth import linkedin_auth
from linkedin.callback import linkedin_callback
from dashboard.ia_engine import gerar_conteudo

# =========================
# ENV (SEGURAS)
# =========================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MERCADO_PAGO_TOKEN = os.getenv("MERCADO_PAGO_TOKEN")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Supabase não configurado")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

mp = mercadopago.SDK(MERCADO_PAGO_TOKEN) if MERCADO_PAGO_TOKEN else None


# =========================
# FLASK APP
# =========================

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "social_ai_secret"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# =========================
# PLANOS
# =========================

PLANOS = {
    "basic": {"nome": "Basic", "preco": 19.90, "limite": 50},
    "pro": {"nome": "Pro", "preco": 39.90, "limite": 200},
    "business": {"nome": "Business", "preco": 79.90, "limite": 999999}
}


# =========================
# PLANOS PAGE
# =========================

@app.route("/planos")
def planos():

    if "user" not in session:
        return redirect("/login")

    return render_template("planos.html", planos=PLANOS)


# =========================
# CHECKOUT
# =========================

@app.route("/checkout/<plano>")
def checkout(plano):

    if "user" not in session:
        return redirect("/login")

    if not mp:
        return "Mercado Pago não configurado"

    if plano not in PLANOS:
        return "Plano inválido"

    user_id = session["user"]
    email = session["email"]

    plano_info = PLANOS[plano]

    preference_data = {
        "items": [
            {
                "title": f"Plano {plano_info['nome']}",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": float(plano_info["preco"])
            }
        ],
        "payer": {"email": email},
        "back_urls": {
            "success": "https://SEU_DOMINIO/sucesso",
            "failure": "https://SEU_DOMINIO/falha",
            "pending": "https://SEU_DOMINIO/pendente"
        },
        "auto_return": "approved",
        "external_reference": f"{user_id}|{plano}"
    }

    preference = mp.preference().create(preference_data)

    return redirect(preference["response"]["init_point"])


# =========================
# WEBHOOK
# =========================

@app.route("/webhook/mercadopago", methods=["POST"])
def webhook_mp():

    if not mp:
        return "ok"

    data = request.get_json(silent=True)

    if not data:
        return "ok"

    try:
        payment_id = data.get("data", {}).get("id")

        if not payment_id:
            return "ok"

        payment = mp.payment().get(payment_id)
        payment_info = payment["response"]

        if payment_info.get("status") == "approved":

            external_reference = payment_info.get("external_reference", "")
            if "|" not in external_reference:
                return "ok"

            user_id, plano = external_reference.split("|")

            plano_info = PLANOS.get(plano)

            if plano_info:

                supabase.table("users").update({
                    "plano": plano,
                    "posts_limite": plano_info["limite"]
                }).eq("id", user_id).execute()

                print("Plano atualizado:", user_id, plano)

    except Exception as e:
        print("Webhook error:", str(e))

    return "ok"


# =========================
# LIMITE
# =========================

def verificar_limite(user_id):

    res = supabase.table("users").select("*").eq("id", user_id).execute()

    if not res.data:
        return False, "Usuário não encontrado"

    user = res.data[0]

    if user.get("plano") == "business":
        return True, "ok"

    if user.get("posts_usados", 0) >= user.get("posts_limite", 10):
        return False, "Limite atingido"

    return True, "ok"


# =========================
# IA GENERATOR
# =========================

@app.route("/ia", methods=["GET", "POST"])
def ia():

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        try:

            tema = request.form["tema"]

            rede = request.form["rede"]

            modo = request.form["modo"]

            nicho = request.form["nicho"]

            data_postagem = request.form["data"]

            hora_postagem = request.form["hora"]

            # =========================
            # IA
            # =========================

            resultado = gerar_conteudo(
                tema,
                rede,
                modo,
                nicho
            )

            if not resultado["success"]:

                return render_template(
                    "ia.html",
                    erro=resultado["erro"]
                )

            conteudo = resultado["conteudo"]

            # =========================
            # SALVAR POST
            # =========================

            supabase.table("posts").insert({

                "tema": tema,

                "rede": rede,

                "conteudo": conteudo,

                "modo": resultado["modo"],

                "nicho": resultado["nicho"],

                "data_postagem": data_postagem,

                "hora_postagem": hora_postagem,

                "status": "pendente",

                "user_id": session["user"]

            }).execute()

            return render_template(
                "ia.html",
                sucesso=True,
                conteudo=conteudo
            )

        except Exception as e:

            print("ERRO IA:", str(e))

            return render_template(
                "ia.html",
                erro=str(e)
            )

    return render_template("ia.html")


# =========================
# CONFIGURAÇÕES
# =========================

@app.route("/configuracoes")
def configuracoes():

    if "user" not in session:
        return redirect("/login")

    try:

        usuario = supabase.table("users") \
            .select("*") \
            .eq("id", session["user"]) \
            .execute()

        if not usuario.data:

            return render_template(
                "configuracoes.html",
                erro="Usuário não encontrado"
            )

        user = usuario.data[0]

        linkedin_conectado = bool(
            user.get("linkedin_token")
        )

        return render_template(
            "configuracoes.html",
            user=user,
            linkedin_conectado=linkedin_conectado
        )

    except Exception as e:

        print("ERRO CONFIG:", str(e))

        return render_template(
            "configuracoes.html",
            erro=str(e)
        )
# =========================
# PUBLICAÇÕES
# =========================

@app.route("/publicacoes")
def publicacoes():

    if "user" not in session:
        return redirect("/login")

    try:

        posts = supabase.table("posts") \
            .select("*") \
            .eq("user_id", session["user"]) \
            .in_("status", ["executado", "erro"]) \
            .order("id", desc=True) \
            .execute()

        return render_template(
            "publicacoes.html",
            posts=posts.data
        )

    except Exception as e:

        return render_template(
            "publicacoes.html",
            erro=str(e)
        )


# =========================
# HOME
# =========================

@app.route("/")
def home():

    if "user" not in session:
        return redirect("/login")

    user_id = session["user"]

    posts = supabase.table("posts") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute().data

    return render_template("index.html", posts=posts)


# =========================
# AGENDAMENTOS
# =========================

@app.route("/agendamentos")
def agendamentos():

    if "user" not in session:
        return redirect("/login")

    try:

        posts = supabase.table("posts") \
            .select("*") \
            .eq("user_id", session["user"]) \
            .order("id", desc=True) \
            .execute()

        return render_template(
            "agendamentos.html",
            posts=posts.data
        )

    except Exception as e:

        return render_template(
            "agendamentos.html",
            erro=str(e)
        )


# =========================
# LINKEDIN
# =========================
@app.route("/linkedin/auth")
def linkedin_oauth():

    if "user" not in session:
        return redirect("/login")

    return linkedin_auth()

# =========================
# CALLBACK LINKEDIN
# =========================

@app.route("/linkedin/callback")
def linkedin_callback_route():

    return linkedin_callback()


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
            return render_template("login.html", erro="Login inválido")

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

            return render_template("register.html", sucesso="Conta criada")

        except Exception as e:
            print(e)
            return render_template("register.html", erro="Erro")

    return render_template("register.html")

# =========================
# EXCLUIR POST
# =========================

@app.route("/delete_post/<post_id>")
def delete_post(post_id):

    if "user" not in session:
        return redirect("/login")

    try:

        supabase.table("posts") \
            .delete() \
            .eq("id", post_id) \
            .eq("user_id", session["user"]) \
            .execute()

        return redirect("/agendamentos")

    except Exception as e:

        return str(e)


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
        .execute().data

    if not post:
        return "Acesso negado"

    supabase.table("posts") \
        .update({"status": "executado"}) \
        .eq("id", post_id) \
        .execute()

    user = supabase.table("users") \
        .select("*") \
        .eq("id", user_id) \
        .execute().data

    if user:
        supabase.table("users") \
            .update({
                "posts_usados": user[0].get("posts_usados", 0) + 1
            }) \
            .eq("id", user_id) \
            .execute()

    return redirect("/")
