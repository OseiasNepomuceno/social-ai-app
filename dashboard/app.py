import os
from datetime import timedelta
import mercadopago
from flask import (
    Flask,
    render_template,
    redirect,
    request,
    session,
    jsonify,
    send_from_directory,
    flash,
    url_for
)
from supabase import create_client
from apscheduler.schedulers.background import BackgroundScheduler

# Importações dos seus agentes internos
from dashboard.agents.analisador_media import gerar_relatorio_completo
from services.supabase_storage import upload_image
from dashboard.agents.media_selector import selecionar_imagem
from dashboard.ia_engine import gerar_conteudo

# =========================
# CONFIGURAÇÃO UNIFICADA E BLINDADA DO FLASK
# =========================

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates"
)

# AJUSTE: Forçando uma chave estática padrão caso a env mude ou suma no reboot do Render.
app.secret_key = os.getenv(
    "SECRET_KEY",
    "social_ai_chave_mestra_estatica_coregov_2026"
)

# AJUSTE: Definindo o tempo de vida máximo de inatividade para 4 horas exatas
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=4)

# AJUSTE: Parâmetros de segurança e persistência dos cookies de navegação
app.config['SESSION_COOKIE_NAME'] = 'social_ai_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True   
app.config['SESSION_COOKIE_SECURE'] = True     
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  

# ROTA DO FAVICON:
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

# =========================
# SUPABASE
# =========================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# =========================
# MERCADO PAGO
# =========================

MERCADO_PAGO_TOKEN = os.getenv("MERCADO_PAGO_TOKEN")
mp = mercadopago.SDK(MERCADO_PAGO_TOKEN) if MERCADO_PAGO_TOKEN else None

# =========================
# PLANOS
# =========================

PLANOS = {
    "free": {
        "nome": "Free",
        "preco": 0,
        "limite": 10
    },
    "pro": {
        "nome": "Pro",
        "preco": 49.90,
        "limite": 60  # Alinhado com 30 posts + 30 stories descritos na UI
    }
}

# =========================
# MONITORAMENTO
# =========================

ADMIN_EMAIL = "oseiasnepom@gmail.com"

@app.route('/monitoramento')
def monitoramento():
    if "user_id" not in session:
        return redirect("/login")
        
    if session.get("email") != ADMIN_EMAIL:
        print(f"🚨 Tentativa de acesso não autorizado ao monitoramento por: {session.get('email')}")
        return redirect("/")

    try:
        relatorio = gerar_relatorio_completo()
    except Exception as e:
        print("Erro ao gerar relatório do monitoramento:", str(e))
        relatorio = {}
        
    return render_template('monitoramento.html', data=relatorio)

# =========================
# FUNÇÕES DE PAGAMENTO & SCHEDULER
# =========================

def verificar_e_atualizar_pagamento(user_id):
    try:
        print("\n========================")
        print(f"🔎 VERIFICANDO PAGAMENTOS - USER: {user_id}")
        print("========================")

        if not mp:
            print("❌ MERCADO PAGO NÃO CONFIGURADO")
            return {"success": False, "message": "Mercado Pago não configurado"}

        pagamentos_response = mp.payment().search({"external_reference": user_id})
        results = pagamentos_response.get("response", {}).get("results", [])

        print(f"PAGAMENTOS ENCONTRADOS: {len(results)}")

        if not results:
            print("⚠️ NENHUM PAGAMENTO ENCONTRADO")
            return {"success": False, "message": "Nenhum pagamento encontrado"}

        for pagamento in results:
            status = pagamento.get("status")
            payment_id = pagamento.get("id")

            print(f"PAGAMENTO ID: {payment_id} | STATUS: {status}")

            if status == "approved":
                print(f"✅ PAGAMENTO APROVADO - {payment_id}")

                supabase.table("users").update({
                    "plano": "pro",
                    "posts_limite": 60
                }).eq("id", user_id).execute()

                print(f"🚀 PLANO PRO ATIVADO - {user_id}")

                return {
                    "success": True,
                    "message": "Plano updated com sucesso",
                    "payment_id": payment_id
                }

        print("⚠️ NENHUM PAGAMENTO APROVADO")
        return {"success": False, "message": "Nenhum pagamento em status aprovado"}

    except Exception as e:
        print(f"❌ ERRO NA VERIFICAÇÃO: {str(e)}")
        return {"success": False, "message": str(e)}

def verificar_pagamentos_todos_usuarios():
    try:
        print("\n" + "="*50)
        print("🔄 VERIFICAÇÃO AUTOMÁTICA DE PAGAMENTOS")
        print("="*50)

        usuarios_free = supabase.table("users").select("id").eq("plano", "free").execute()
        usuarios = usuarios_free.data

        print(f"USUÁRIOS FREE: {len(usuarios)}")

        if not usuarios:
            print("✅ NENHUM USUÁRIO PARA VERIFICAR")
            return
        
        for usuario in usuarios:
            user_id = usuario["id"]
            resultado = verificar_e_atualizar_pagamento(user_id)
            if resultado["success"]:
                print(f"✅ {user_id}: {resultado['message']}")
            else:
                print(f"⚠️ {user_id}: {resultado['message']}")

    except Exception as e:
        print(f"❌ ERRO NA TAREFA AGENDADA: {str(e)}")

# Inicialização segura do Scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=verificar_pagamentos_todos_usuarios,
    trigger="interval",
    minutes=15,
    id="verificar_pagamentos",
    name="Verificar pagamentos pendentes",
    replace_existing=True
)
scheduler.start()
print("✅ SCHEDULER INICIADO - Verificação a cada 15 minutos")

# =========================
# ROTAS DE HOME E AUTENTICAÇÃO
# =========================

@app.route("/")
def home():
    if "user_id" not in session:
        return redirect("/login")

    try:
        posts = supabase.table("posts").select("*").eq(
            "user_id", session["user_id"]
        ).order("id", desc=True).limit(6).execute().data

        total_posts = len(posts)
        executados = len([p for p in posts if p.get("status") == "executado"])
        pendentes = len([p for p in posts if p.get("status") == "pendente"])
        erros = len([p for p in posts if p.get("status") == "erro"])

        return render_template(
            "index.html",
            posts=posts,
            total_posts=total_posts,
            executados=executados,
            pendentes=pendentes,
            erros=erros
        )
    except Exception as e:
        print("HOME ERROR:", str(e))
        return render_template("index.html", posts=[], total_posts=0, executados=0, pendentes=0, erros=0, erro=str(e))

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
            session.permanent = True
            session["user_id"] = user.id
            session["email"] = user.email

            checar_usuario = supabase.table("users").select("plano").eq("id", user.id).execute()
            
            if not checar_usuario.data:
                supabase.table("users").insert({
                    "id": user.id,
                    "email": user.email,
                    "plano": "free",
                    "posts_limite": 10,
                    "posts_usados": 0
                }).execute()
            else:
                supabase.table("users").update({
                    "email": user.email
                }).eq("id", user.id).execute()

            return redirect("/")

        except Exception as e:
            print("LOGIN ERROR:", str(e))
            return render_template(
                "login.html",
                erro="Login inválido. Verifique suas credenciais ou confirme seu e-mail."
            )

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]

        try:
            resposta = supabase.auth.sign_up({
                "email": email,
                "password": senha
            })
            
            user = resposta.user
            if not user:
                return render_template("register.html", erro="Erro ao criar conta.")

            supabase.table("users").upsert({
                "id": user.id,
                "nome": nome,
                "email": email,
                "plano": "free",
                "posts_limite": 10,
                "posts_usados": 0
            }).execute()

            session.permanent = True
            session["user_id"] = user.id
            session["email"] = email

            print("✅ USUÁRIO CRIADO VIA AUTH")
            return redirect("/")

        except Exception as e:
            print("REGISTER ERROR:", str(e))
            return render_template("register.html", erro="Erro ao criar conta.")

    return render_template("register.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("email", None)
    return redirect("/login")

# =========================
# GERADOR INTELIGENTE DE POSTS (IA)
# =========================

@app.route("/ia", methods=["GET", "POST"])
def ia():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        try:
            # Captura mapeada perfeitamente com os 'name' do novo arquivo ia.html
            tema = request.form.get("tema")
            rede = request.form.get("rede_social")
            modo = request.form.get("modo")
            nicho = request.form.get("nicho")
            data_postagem = request.form.get("data_postagem")
            hora_postagem = request.form.get("horario")

            print(f"🚀 EXECUTOR IA ACIONADO: Tema='{tema}' | Rede='{rede}' | Modo='{modo}'")

            status_post = "pronto_instagram" if (rede and rede.lower() == "instagram") else "pendente"
            imagem_url = None

            # 🛠️ Validação e Upload da Imagem Própria
            file = request.files.get("imagem")
            if file and file.filename != "":
                print(f"📸 Imagem manual detectada: {file.filename}. Iniciando upload...")
                upload_result = upload_image(file)
                if upload_result.get("success"):
                    imagem_url = upload_result.get("public_url")
                    print(f"✅ Upload concluído com sucesso. URL: {imagem_url}")

            # 🏢 Estratégia de Fallback: Se não mandou foto, busca do banco de mídias (Supabase)
            if not imagem_url:
                print("📂 Nenhuma imagem enviada. Buscando na Media Library do Supabase...")
                imagem_url = selecionar_imagem(nicho=nicho, rede=rede, estilo="premium")
                print(f"🎯 Imagem selecionada do banco: {imagem_url}")

            # Geração da Copy via IA Engine
            resultado = gerar_conteudo(tema, rede, modo, nicho)

            if not resultado.get("success"):
                flash(f"Erro na inteligência artificial: {resultado.get('erro')}", "error")
                return redirect(url_for("ia"))

            conteudo = resultado["conteudo"]

            # Montagem estruturada para persistência no banco de dados do Portal
            payload = {
                "tema": tema,
                "rede": rede,
                "conteudo": conteudo,
                "modo": modo,
                "nicho": nicho,
                "imagem_url": imagem_url,
                "data_postagem": data_postagem,
                "hora_postagem": hora_postagem,
                "status": status_post,
                "user_id": session["user_id"]
            }

            # Salvando o registro na tabela de posts
            supabase.table("posts").insert(payload).execute()
            print("💾 Post inserido com sucesso na tabela 'posts' do Supabase.")

            # Incrementando o contador de posts utilizados do usuário
            user_data = supabase.table("users").select("posts_usados").eq("id", session["user_id"]).execute()
            if user_data.data:
                atual_usados = user_data.data[0].get("posts_usados", 0)
                novo_total = atual_usados + 1
                
                supabase.table("users").update({
                    "posts_usados": novo_total
                }).eq("id", session["user_id"]).execute()
                print(f"增 Contador atualizado! Total usado: {novo_total}")

            # Dispara a mensagem flash de sucesso de volta para a view
            flash("Postagem criada e enviada para agendamentos com sucesso!", "success")
            return redirect(url_for("ia"))

        except Exception as e:
            print("❌ EXCEÇÃO DISPARADA NO EXECUTOR IA:", str(e))
            flash(f"Ocorreu um erro interno no processo: {str(e)}", "error")
            return redirect(url_for("ia"))

    return render_template("ia.html")

# =========================
# OUTRAS DIRETRIZES DA PLATAFORMA
# =========================

@app.route("/agendamentos")
def agendamentos():
    if "user_id" not in session:
        return redirect("/login")
    try:
        posts = supabase.table("posts").select("*").eq("user_id", session["user_id"]).order("id", desc=True).execute().data
        return render_template("agendamentos.html", posts=posts)
    except Exception as e:
        return render_template("agendamentos.html", erro=str(e), posts=[])

@app.route("/deletar/<int:post_id>")
def deletar_post(post_id):
    if "user_id" not in session:
        return redirect("/login")
    try:
        supabase.table("posts").delete().eq("id", post_id).eq("user_id", session["user_id"]).execute()
        return redirect("/agendamentos")
    except Exception as e:
        return str(e)

@app.route("/publicacoes")
def publicacoes():
    if "user_id" not in session:
        return redirect("/login")
    try:
        posts = supabase.table("posts").select("*").eq("user_id", session["user_id"]).in_("status", ["executado", "pronto_instagram"]).order("id", desc=True).execute().data
        return render_template("publicacoes.html", posts=posts)
    except Exception as e:
        return render_template("publicacoes.html", erro=str(e), posts=[])

@app.route("/configuracoes")
def configuracoes():
    if "user_id" not in session:
        return redirect("/login")
    try:
        usuario = supabase.table("users").select("*").eq("id", session["user_id"]).execute()
        
        if not usuario.data:
            user_backup = {
                "email": session.get("email", "E-mail na Sessão"),
                "plano": "free"
            }
            return render_template("configuracoes.html", user=user_backup, linkedin_conectado=False)
        
        user = usuario.data[0]
        linkedin_conectado = bool(user.get("linkedin_token"))
        return render_template("configuracoes.html", user=user, linkedin_conectado=linkedin_conectado)
    except Exception as e:
        print("CONFIG ERROR BACKUP ACTIVE:", str(e))
        user_backup = {"email": session.get("email", "E-mail na Sessão"), "plano": "free"}
        return render_template("configuracoes.html", user=user_backup, linkedin_conectado=False)

@app.route("/planos")
def planos():
    if "user_id" not in session:
        return redirect("/login")
    try:
        verificar_e_atualizar_pagamento(session["user_id"])
        
        busca_user = supabase.table("users").select("*").eq("id", session["user_id"]).execute()
        usuario_atual = busca_user.data[0] if busca_user.data else None
        
        return render_template("planos.html", planos=PLANOS, usuario=usuario_atual)
    except Exception as e:
        print("ERRO ROTA PLANOS:", str(e))
        return str(e)

@app.route("/checkout/pro")
def checkout_pro():
    if "user_id" not in session:
        return redirect("/login")
    try:
        preference_data = {
            "items": [{"title": "Social AI Pro", "quantity": 1, "currency_id": "BRL", "unit_price": 49.90}],
            "payer": {"email": session["email"]},
            "back_urls": {
                "success": "https://app.coregov.com.br/planos",
                "failure": "https://app.coregov.com.br/planos",
                "pending": "https://app.coregov.com.br/planos"
            },
            "auto_return": "approved",
            "external_reference": session["user_id"]
        }
        preference = mp.preference().create(preference_data)["response"]
        return redirect(preference["init_point"])
    except Exception as e:
        return str(e)

@app.route("/webhook/mercadopago", methods=["POST"])
def webhook_mercadopago():
    try:
        data = request.json
        if not data:
            return {"success": False}, 400

        payment_type = data.get("type") or data.get("topic")
        if payment_type != "payment":
            return {"success": True}, 200

        payment_id = data["data"].get("id") if "data" in data else data.get("id")
        if not payment_id:
            return {"success": False}, 400

        payment = mp.payment().get(payment_id)["response"]
        if payment.get("status") != "approved":
            return {"success": True}, 200

        user_id = payment.get("external_reference")
        if not user_id:
            return {"success": False}, 400

        supabase.table("users").update({"plano": "pro", "posts_limite": 60}).eq("id", user_id).execute()
        return {"success": True}, 200
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

if __name__ == "__main__":
    app.run(debug=True)
