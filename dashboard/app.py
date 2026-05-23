import os
from datetime import datetime, timedelta
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
    url_for,
    render_template_string  # Suporte à tela de transição do Google
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
# MIDDLEWARE: MONITORAMENTO DE TRÁFEGO (SÉRIE TEMPORAL)
# =========================

@app.before_request
def rastrear_atividade_usuario():
    # Ignora checagem para arquivos estáticos e favicon para não sobrecarregar o banco
    if request.path.startswith('/static') or request.path == '/favicon.ico':
        return

    if "user_id" in session:
        user_id = session["user_id"]
        agora_iso = datetime.utcnow().isoformat()
        hoje_str = datetime.utcnow().strftime("%Y-%m-%d")

        try:
            # 1. Atualiza o timestamp de última atividade em tempo real na tabela de usuários
            supabase.table("users").update({
                "ultima_atividade": agora_iso
            }).eq("id", user_id).execute()

            # 2. Registra a presença diária única para geração do histórico/gráficos
            # Usamos uma estratégia de upsert combinando user_id e data_acesso para evitar duplicados no mesmo dia
            id_registro_unico = f"{user_id}_{hoje_str}"
            supabase.table("analytics_acessos").upsert({
                "id_composto": id_registro_unico,
                "user_id": user_id,
                "data_acesso": hoje_str
            }).execute()

        except Exception as e:
            # Silencioso no console para não quebrar a experiência do usuário se o banco oscilar
            print(f"⚠️ Erro ao registrar tracking de analytics: {str(e)}")

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

    # --- 1. CÁLCULO DE MÉTRICAS VIA SUPABASE ---
    usuarios_online = 0
    usuarios_hoje = 0
    usuarios_mes = 0
    grafico_labels = []
    grafico_dados = []

    try:
        agora = datetime.utcnow()
        
        # Tempo Real: Usuários que interagiram nos últimos 5 minutos
        cinco_minutos_atras = (agora - timedelta(minutes=5)).isoformat()
        res_online = supabase.table("users").select("id", count="exact").gte("ultima_atividade", cinco_minutos_atras).execute()
        usuarios_online = res_online.count if res_online.count is not None else 0

        # Histórico: Hoje
        hoje_str = agora.strftime("%Y-%m-%d")
        res_hoje = supabase.table("analytics_acessos").select("user_id", count="exact").eq("data_acesso", hoje_str).execute()
        usuarios_hoje = res_hoje.count if res_hoje.count is not None else 0

        # Histórico: Últimos 30 dias (Mês)
        trinta_dias_atras = (agora - timedelta(days=30)).strftime("%Y-%m-%d")
        res_mes = supabase.table("analytics_acessos").select("user_id", count="exact").gte("data_acesso", trinta_dias_atras).execute()
        usuarios_mes = res_mes.count if res_mes.count is not None else 0

        # --- 2. CONSTRUÇÃO DO GRÁFICO (ÚLTIMOS 7 DIAS) ---
        for i in range(6, -1, -1):
            dia_alvo = agora - timedelta(days=i)
            dia_alvo_str = dia_alvo.strftime("%Y-%m-%d")
            dia_exibicao = dia_alvo.strftime("%d/%m")
            
            # Busca contagem de acessos específicos daquele dia
            res_dia = supabase.table("analytics_acessos").select("user_id", count="exact").eq("data_acesso", dia_alvo_str).execute()
            total_dia = res_dia.count if res_dia.count is not None else 0
            
            grafico_labels.append(dia_exibicao)
            grafico_dados.append(total_dia)

    except Exception as err_metrics:
        print(f"⚠️ Falha ao computar métricas de usuários: {str(err_metrics)}")

    # --- 3. SAÚDE DOS AGENTES (LOGS) ---
    try:
        relatorio = gerar_relatorio_completo()
    except Exception as e:
        print("Erro ao gerar relatório do monitoramento:", str(e))
        relatorio = {}
        
    return render_template(
        'monitoramento.html', 
        data=relatorio,
        usuarios_online=usuarios_online,
        usuarios_hoje=usuarios_hoje,
        usuarios_mes=usuarios_mes,
        grafico_labels=grafico_labels,
        grafico_dados=grafico_dados
    )

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

        total_posts = len(posts) if posts else 0
        executados = 0
        pendentes = 0
        erros = 0

        if posts:
            for p in posts:
                status = p.get("status")
                if status == "executado":
                    executados += 1
                elif status == "pendente":
                    pendentes += 1
                elif status == "erro":
                    erros += 1

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
                erro="Login inválido. Verifique suas credenciais ou tente fazer login com o Google."
            )

    return render_template("login.html")

# 🌐 INTEGRADO: Rota para Disparar a Autenticação OAuth do Google no Supabase
@app.route("/login/google")
def login_google():
    try:
        dados_auth = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": "https://app.coregov.com.br/auth/callback"
            }
        })
        return redirect(dados_auth.url)
    except Exception as e:
        print(f"❌ ERRO AO INICIAR FLUXO GOOGLE OAUTH: {str(e)}")
        return redirect("/login")

# 🌐 CORREÇÃO DEFINITIVA: Rota de Retorno (Callback) Inteligente para Code Flow (?code=) e Hash Flow
@app.route("/auth/callback")
def auth_callback():
    try:
        # 1. Verifica se o Google enviou o código de autenticação limpo (Code Flow)
        code = request.args.get("code")
        
        if code:
            print(f"🎟️ Código de Autenticação detectado (?code={code[:6]}...). Trocando por sessão...")
            resposta = supabase.auth.exchange_code_for_session({"auth_code": code})
        else:
            # 2. Fallback: Tenta capturar os tokens se eles vieram tratados pelo script JavaScript
            access_token = request.args.get("access_token")
            refresh_token = request.args.get("refresh_token")
            
            if access_token and refresh_token:
                print("🔑 Tokens detectados na URL. Configurando sessão estruturada no Supabase...")
                supabase.auth.set_session({
                    "access_token": access_token,
                    "refresh_token": refresh_token
                })
                resposta = supabase.auth.get_user(access_token)
            else:
                resposta = None
        
        # 3. Se conseguimos autenticar com sucesso por qualquer uma das vias
        if resposta and hasattr(resposta, 'user') and resposta.user:
            user = resposta.user
            
            # Inicializa de forma estável a sessão do Flask
            session.permanent = True
            session["user_id"] = user.id
            session["email"] = user.email

            print(f"🌐 LOGIN SOCIAL GOOGLE DETERMINADO COM SUCESSO: {user.email}")

            # Sincroniza e cria o perfil na tabela pública 'users' se for a primeira vez
            try:
                supabase.table("users").upsert({
                    "id": user.id,
                    "email": user.email,
                    "plano": "free",
                    "posts_limite": 10,
                    "posts_usados": 0
                }).execute()
                print(f"✅ Usuário Google sincronizado com sucesso na tabela pública 'users'.")
            except Exception as table_err:
                print(f"⚠️ Nota de tabela: {str(table_err)}")

            return redirect("/")
            
        # 4. Caso os dados ainda estejam ocultos atrás do '#' na URL original, aciona o conversor JS
        print("🔄 Aguardando conversão de fragmento de hash da URL do Google OAuth...")
        return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Autenticando...</title>
                <script>
                    window.onload = function() {
                        var hash = window.location.hash.substring(1);
                        if (hash.length > 0) {
                            var params = new URLSearchParams(hash);
                            var accessToken = params.get("access_token");
                            var refreshToken = params.get("refresh_token");
                            if (accessToken && refreshToken) {
                                window.location.href = "/auth/callback?access_token=" + accessToken + "&refresh_token=" + refreshToken;
                                return;
                            }
                        }
                        setTimeout(function() { window.location.href = "/"; }, 1500);
                    };
                </script>
            </head>
            <body style="background:#111827; color:#fff; font-family:sans-serif; display:flex; justify-content:center; align-items:center; height:100vh; margin:0;">
                <div style="text-align:center;">
                    <h2 style="margin-bottom:8px;">Conectando com o Google...</h2>
                    <p style="color:#9ca3af; font-size:14px;">Validando credenciais com segurança de ponta.</p>
                </div>
            </body>
            </html>
        ''')
        
    except Exception as e:
        print(f"❌ ERRO CRÍTICO NO CALLBACK DO GOOGLE: {str(e)}")
        return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]

        try:
            resposta = supabase.auth.sign_up({
                "email": email,
                "password": senha,
                "options": {
                    "data": {
                        "display_name": nome
                    }
                }
            })
            
            user = resposta.user
            
            if not user or not hasattr(user, 'id') or user.id is None:
                print("⚠️ Pré-cadastro efetuado. Aguardando validação de e-mail.")
                return render_template(
                    "register.html", 
                    sucesso="📬 Quase lá! Enviamos um e-mail de ativação para você. Acesse sua caixa de entrada (ou spam) e clique no link de validação. Assim que confirmar, seu acesso será liberado na hora! 🚀"
                )

            try:
                dados_usuario = {
                    "id": user.id,
                    "email": email,
                    "plano": "free",
                    "posts_limite": 10,
                    "posts_usados": 0
                }
                supabase.table("users").upsert(dados_usuario).execute()
                print(f"✅ Usuário saved na tabela pública 'users': {email}")
            except Exception as table_err:
                print(f"⚠️ Alerta ao salvar na tabela 'users': {str(table_err)}")

            session.permanent = True
            session["user_id"] = user.id
            session["email"] = email

            print(f"✅ USUÁRIO CRIADO E LOGADO DIRETAMENTE: {email}")
            return redirect("/")

        except Exception as e:
            error_msg = str(e)
            print(f"❌ REGISTER ERROR CAPTURADO NO CONSOLE: {error_msg}")
            
            if "User already registered" in error_msg or "already exists" in error_msg:
                user_friendly_error = "Este e-mail já está cadastrado no sistema. Tente fazer login."
            elif "should be at least" in error_msg:
                user_friendly_error = "A senha escolhida é muito fraca. Utilize pelo menos 6 caracteres."
            else:
                user_friendly_error = "Houve uma instabilidade temporária ao salvar seus dados. Verifique suas informações e tente novamente."
                
            return render_template("register.html", erro=user_friendly_error)

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
            tema = request.form.get("tema")
            rede = request.form.get("rede_social")
            modo = request.form.get("modo")
            nicho = request.form.get("nicho")
            data_postagem = request.form.get("data_postagem")
            hora_postagem = request.form.get("horario")

            print(f"🚀 EXECUTOR IA ACIONADO: Tema='{tema}' | Rede='{rede}' | Modo='{modo}'")

            status_post = "pronto_instagram" if (rede and rede.lower() == "instagram") else "pendente"
            imagem_url = None

            file = request.files.get("imagem")
            if file and file.filename != "":
                print(f"📸 Imagem manual detectada: {file.filename}. Iniciando upload...")
                upload_result = upload_image(file)
                if upload_result.get("success"):
                    imagem_url = upload_result.get("public_url")
                    print(f"✅ Upload concluído com sucesso. URL: {imagem_url}")

            if not imagem_url:
                print("📂 Nenhuma imagem enviada. Buscando na Media Library do Supabase...")
                imagem_url = selecionar_imagem(nicho=nicho, rede=rede, estilo="premium")
                print(f"🎯 Imagem selecionada do banco: {imagem_url}")

            resultado = gerar_conteudo(tema, rede, modo, nicho)

            if not resultado.get("success"):
                flash(f"Erro na inteligência artificial: {resultado.get('erro')}", "error")
                return redirect(url_for("ia"))

            conteudo = resultado["conteudo"]

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

            supabase.table("posts").insert(payload).execute()
            print("💾 Post inserido com sucesso na tabela 'posts' do Supabase.")

            user_data = supabase.table("users").select("posts_usados").eq("id", session["user_id"]).execute()
            if user_data.data:
                atual_usados = user_data.data[0].get("posts_usados", 0)
                novo_total = atual_usados + 1
                
                supabase.table("users").update({
                    "posts_usados": novo_total
                }).eq("id", session["user_id"]).execute()
                print(f"Contador updated! Total usado: {novo_total}")

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
        posts = supabase.table("posts").select("*").eq(
            "user_id", session["user_id"]
        ).in_("status", ["executado", "pronto_instagram"]).order("id", desc=True).execute().data
        
        return render_template("publicacoes.html", posts=posts)
    except Exception as e:
        print("ERRO ROTA PUBLICACOES:", str(e))
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
