import os
from datetime import datetime, timedelta
import threading  # 🚀 SOLUÇÃO: Importado para rodar o robô em segundo plano de forma assíncrona
import requests   # 🔗 ADICIONADO: Necessário para a troca de tokens na rota de callback do LinkedIn
import mercadopago
import urllib.parse # Importe isso no topo do arquivo
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

# AGENTE DE VARIAÇÃO: Importando o pipeline de multiplicação automática
#from dashboard.agents.media_variation_agent import iniciar_multiplicacao_banco_existente

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

# AJUSTE: Definindo o tempo de vida máximo de inatividade para 4 hours exatas
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=4)

# AJUSTE: Parâmetros de segurança e persistência dos cookies de navegação
app.config['SESSION_COOKIE_NAME'] = 'social_ai_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True   
app.config['SESSION_COOKIE_SECURE'] = True     
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  

# =========================
# ROTA DO FAVICON:
# =========================

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

# =========================
# FUNDO ANIMADO
# =========================

@app.route("/fundo")
def fundo_video():
    return render_template("fundo-video.html")

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
        "preco": 99.90,  # 🔥 Atualizado para R$ 99,90 conforme solicitado!
        "limite": 60  # Alinhado com 30 posts + 30 stories descritos na UI
    }
}


# --- ROTA 1: INÍCIO DO FLUXO (O botão que você coloca no HTML) ---

@app.route("/instagram/login")
def instagram_login():
    # 1. Remova 'email' se não for estritamente necessário agora
    # 2. Use os escopos que estão com check verde no seu painel (print image_ab6f1b.png)
    # Use apenas estas permissões que já estão configuradas no seu painel
    # Mude para isso, removendo a permissão que está dando erro
    
    scope = (
    "instagram_basic,"
    "instagram_manage_comments,"
    "pages_show_list,"
    "pages_read_engagement,"
    "business_management"
    )
    
    auth_url = (
        f"https://www.facebook.com/v21.0/dialog/oauth?"
        f"client_id={os.getenv('FACEBOOK_APP_ID')}"
        f"&redirect_uri=https://app.coregov.com.br/facebook/callback"
        f"&scope={scope}"
        f"&response_type=code"
        f"&state={session.get('user_id', 'init')}"
        f"&auth_type=rerequest" 
    )
    return redirect(auth_url)

# --- ROTA 2, 3 e 4: O CALLBACK (Onde a mágica acontece) ---
@app.route('/facebook/callback')
def facebook_callback():

    user_id = request.args.get("state")

    code = request.args.get("code")

    if not code:
        return "Código OAuth não recebido", 400

    FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
    FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")
    
    token_url = (
        "https://graph.facebook.com/v21.0/oauth/access_token"
        f"?client_id={FACEBOOK_APP_ID}"
        f"&redirect_uri=https://app.coregov.com.br/facebook/callback"
        f"&client_secret={FACEBOOK_APP_SECRET}"
        f"&code={code}"
    )

    token_response = requests.get(token_url)
    token_data = token_response.json()
    
    print("TOKEN RESPONSE:", token_data)
    
    if "access_token" not in token_data:
        return f"Erro ao obter token: {token_data}", 400
    
    access_token = token_data["access_token"]
    # ... (seu código de troca de token) ...
    
    # Após pegar o access_token, verifique a resposta antes de usar
    me_url = f"https://graph.facebook.com/v21.0/me/accounts?access_token={access_token}"
    response = requests.get(me_url)
    pages = response.json()
    print("PAGES RESPONSE:")
    print(pages)
    print("ACCESS TOKEN:")
    print(access_token[:20])
    
    # PROTEÇÃO AQUI:
    if 'data' not in pages:
        return f"Erro na API do Facebook: {pages.get('error', 'Sem dados de páginas')}", 400
        
    if len(pages['data']) == 0:
        return "Você não selecionou nenhuma página na tela do Facebook!", 400

    page_id = pages['data'][0]['id']
    # ... restante ...
    page_token = pages['data'][0]['access_token']

    # Agora buscamos o ID da conta do Instagram atrelada a essa página
    insta_url = f"https://graph.facebook.com/v21.0/{page_id}?fields=instagram_business_account&access_token={page_token}"
    insta_data = requests.get(insta_url).json()
    
    if "instagram_business_account" not in insta_data:
        return f"Instagram não vinculado à página: {insta_data}", 400

    insta_id = insta_data["instagram_business_account"]["id"]
   
    # PASSO 4: Armazenar tudo no Supabase
    supabase.table("users").update({
        "instagram_token": access_token,
        "instagram_business_id": insta_id
    }).eq("id", user_id).execute()
    
    return "Conectado com sucesso! Agora você pode voltar ao sistema."


# =========================
# ROBOTS.TXT
# =========================

@app.route('/robots.txt')
def robots_txt():
    linhas = [
        "User-agent: *",          # Se aplica a TODOS os robôs (Google, OpenAI, Bing)
        "Disallow: /dashboard",   # Proíbe de indexar a área logada (se houver essa rota)
        "Disallow: /api/",        # Proíbe de ler suas rotas internas de API
        "Allow: /$"               # Permite indexar APENAS a página inicial institucional
    ]
    return "\n".join(linhas), 200, {'Content-Type': 'text/plain'}

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
            id_registro_unico = f"{user_id}_{hoje_str}"
            supabase.table("analytics_acessos").upsert({
                "id_composto": id_registro_unico,
                "user_id": user_id,
                "data_acesso": hoje_str
            }).execute()

        except Exception as e:
            print(f"⚠️ Erro ao registrar tracking de analytics: {str(e)}")

# =========================
# MONITORAMENTO (CORRIGIDA COM THREADS)
# =========================

ADMIN_EMAIL = "oseiasnepom@gmail.com"

@app.route('/monitoramento')
def monitoramento():
    if "user_id" not in session:
        return redirect("/login")
        
    if session.get("email") != ADMIN_EMAIL:
        print(f"🚨 Tentativa de acesso não autorizado ao monitoramento por: {session.get('email')}")
        return redirect("/")

    # ⚡ SOLUÇÃO DE TIMEOUT: Mantendo seu robô assíncrono em segundo plano ativo e seguro
    try:
        print("⚡ Gatilho detectado via Painel Admin: Disparando robô multiplicador...")
        thread_agente = threading.Thread(
            target=iniciar_multiplicacao_banco_existente,
            kwargs={"limite_por_rodada": 20},
            daemon=True
        )
        thread_agente.start()
    except Exception as err_agente:
        print(f"⚠️ Falha ao criar a thread de multiplicação: {str(err_agente)}")

    # Inicialização das variáveis limpas para evitar quebras
    usuarios_online = 0
    usuarios_hoje = 0
    usuarios_mes = 0
    lista_online = []
    lista_hoje = []
    lista_mes = []
    grafico_labels = []
    grafico_dados = []

    try:
        agora = datetime.utcnow()
        
        # --- 1. USUÁRIOS ONLINE (Últimos 5 minutos) ---
        cinco_minutos_atras = (agora - timedelta(minutes=5)).isoformat()
        res_online = supabase.table("users").select("id", "email").gte("ultima_atividade", cinco_minutos_atras).execute()
        if res_online.data:
            lista_online = res_online.data
            usuarios_online = len(lista_online)

        # --- 2. ACESSOS HOJE ---
        hoje_str = agora.strftime("%Y-%m-%d")
        res_hoje = supabase.table("analytics_acessos").select("user_id", "users(email)").eq("data_acesso", hoje_str).execute()
        if res_hoje.data:
            lista_hoje = [{"email": item["users"]["email"]} for item in res_hoje.data if item.get("users")]
            usuarios_hoje = len(lista_hoje)

        # --- 3. ACESSOS NO MÊS (Últimos 30 dias) ---
        trinta_dias_atras = (agora - timedelta(days=30)).strftime("%Y-%m-%d")
        res_mes = supabase.table("analytics_acessos").select("user_id", "users(email)").gte("data_acesso", trinta_dias_atras).execute()
        if res_mes.data:
            emails_unicos_mes = {item["users"]["email"] for item in res_mes.data if item.get("users")}
            lista_mes = [{"email": email} for email in emails_unicos_mes]
            usuarios_mes = len(lista_mes)

        # --- 4. CONSTRUÇÃO DO GRÁFICO (ÚLTIMOS 7 DIAS) ---
        for i in range(6, -1, -1):
            dia_alvo = agora - timedelta(days=i)
            dia_alvo_str = dia_alvo.strftime("%Y-%m-%d")
            dia_exibicao = dia_alvo.strftime("%d/%m")
            
            res_dia = supabase.table("analytics_acessos").select("user_id", count="exact").eq("data_acesso", dia_alvo_str).execute()
            total_dia = res_dia.count if res_dia.count is not None else 0
            
            grafico_labels.append(dia_exibicao)
            grafico_dados.append(total_dia)

    except Exception as err_metrics:
        print(f"⚠️ Falha crítica ao computar métricas de usuários: {str(err_metrics)}")

    # --- 5. SAÚDE DOS AGENTES ---
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
        lista_online=lista_online,
        lista_hoje=lista_hoje,
        lista_mes=lista_mes,
        grafico_labels=grafico_labels,
        grafico_dados=grafico_dados
    )

# =========================
# CONEXÃO OAUTH LINKEDIN (LOGIN E CALLBACK) ✅ CORRIGIDO
# =========================

@app.route("/linkedin/login", methods=["GET"])
def linkedin_login():
    if "user_id" not in session:
        return redirect("/login")
        
    CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
    REDIRECT_URI = "https://app.coregov.com.br/linkedin/callback"
    
    if not CLIENT_ID:
        print("❌ Erro: LINKEDIN_CLIENT_ID não configurado no ambiente do Render.")
        flash("A integração com o LinkedIn está em manutenção temporária. Contate o suporte.", "danger")
        return redirect(url_for("configuracoes"))
    
    # ✅ CORRIGIDO: Usando APENAS escopos válidos do LinkedIn (removido Instagram)
    scope = "openid,profile,email,w_member_social"
    
    linkedin_auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&state={session['user_id']}"
        f"&scope={scope}"
    )
    
    print(f"🔗 Redirecionando Usuário {session['user_id']} para o fluxo do LinkedIn OAuth.")
    print(f"📋 Escopos solicitados: {scope}")
    return redirect(linkedin_auth_url)


@app.route("/linkedin/callback", methods=["GET"])
def linkedin_callback():
    code = request.args.get("code")
    state = request.args.get("state")  
    error = request.args.get("error")
    error_description = request.args.get("error_description")
    
    if error:
        print(f"❌ Autorização recusada ou cancelada: {error}")
        print(f"📝 Descrição: {error_description}")
        flash("Autorização cancelada ou negada. Verifique as permissões solicitadas.", "warning")
        return redirect(url_for("configuracoes"))
        
    if not code:
        flash("Código de autenticação ausente ou inválido.", "danger")
        return redirect(url_for("configuracoes"))
        
    user_id = state if state else session.get("user_id")
    if not user_id:
        print("❌ Erro: Callback do LinkedIn sem identificador de usuário válido.")
        return redirect("/login")

    CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
    CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
    REDIRECT_URI = "https://app.coregov.com.br/linkedin/callback"

    try:
        print(f"🎟️ Trocando código por token de acesso definitivo para o User {user_id}...")
        
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        response = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data=token_data,
            headers=headers
        )
        
        token_json = response.json()
        
        if "access_token" in token_json:
            access_token = token_json["access_token"]
            print(f"✅ Token do LinkedIn gerado com sucesso. Salvando no Supabase...")
            
            supabase.table("users").update({
                "linkedin_token": access_token
            }).eq("id", user_id).execute()
            
            flash("Sua conta do LinkedIn foi conectada com sucesso! 🚀", "success")
        else:
            print(f"❌ Erro retornado pela API do LinkedIn: {token_json}")
            flash("Não foi possível validar as credenciais junto ao LinkedIn.", "danger")
            
    except Exception as e:
        print(f"❌ ERRO CRÍTICO NO CALLBACK DO LINKEDIN: {str(e)}")
        flash(f"Instabilidade temporária ao conectar com o LinkedIn: {str(e)}", "danger")
        
    return redirect(url_for("configuracoes"))

# =========================
# FUNÇÃO PARA BUSCAR NICHOS ATIVOS NO BANCO
# =========================

# Função para buscar nichos ativos do banco
def buscar_nichos_ativos():
    try:
        response = supabase.table("media_library")\
            .select("nicho")\
            .eq("ativo", True)\
            .group("nicho")\
            .execute()
        
        nichos = [item['nicho'] for item in response.data or []]
        return nichos
    except Exception as e:
        print(f"Erro ao buscar nichos ativos: {str(e)}")
        # lista padrão como fallback
        return [
            "limpeza",
            "marketing",
            "psicologia",
            "negocios",
            "engenharia",
            "financeiro",
            "tecnologia",
            "contabilidade",
            "vendas",
            "empreendedorismo",
            "saude",
            "fotografiadealimentos",
            "fitnessbem-estar",
            "diversidadeerepresentacao",
            "viagenseturismo",
            "saudementalemindfulness",
            "alimentacao",
            "familiaerelacionamentos",
            "arquiteturaedesigndeinteriores",
            "tecnologiamergente",
            "moda",
            "educacao"
        ]

# Função para normalizar texto para comparação
import unicodedata
def normalizar_texto(texto):
    texto = texto.lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    texto = texto.replace(" ", "")
    return texto

# Função para calcular distância de Levenshtein (igual a da ia_engine.py)
def distancia_levenshtein(a, b):
    n, m = len(a), len(b)
    if n > m:
        a, b = b, a
        n, m = m, n

    current = list(range(n + 1))
    for i in range(1, m + 1):
        previous, current = current, [i] + [0] * n
        for j in range(1, n + 1):
            add = previous[j] + 1
            delete = current[j - 1] + 1
            change = previous[j - 1]
            if a[j - 1] != b[i - 1]:
                change += 1
            current[j] = min(add, delete, change)

    return current[n]

# Função para encontrar nicho mais próximo ao tema
def encontrar_nicho_mais_proximo(entrada, lista_nichos):
    entrada_norm = normalizar_texto(entrada)

    melhor_nicho = None
    menor_distancia = float('inf')

    for nicho in lista_nichos:
        nicho_norm = normalizar_texto(nicho)
        dist = distancia_levenshtein(entrada_norm, nicho_norm)
        if dist < menor_distancia:
            menor_distancia = dist
            melhor_nicho = nicho
    return melhor_nicho

# Alteração na rota `/ia` para GET preencher nicho sugerido automaticamente
@app.route("/ia", methods=["GET", "POST"])
def ia():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        # [o conteúdo POST permanece igual, tratado anteriormente]
        # ...
        # (manter todo fluxo POST normal, não alterado)

    else:
        # GET: carrega nicho sugerido para facilitar escolha
        nichos_ativos = buscar_nichos_ativos()
        nicho_sugerido = None

        tema = request.args.get("tema", "")  # caso queira receber via query param

        if tema:
            nicho_sugerido = encontrar_nicho_mais_proximo(tema, nichos_ativos)
            print(f"Nicho sugerido para o tema '{tema}': {nicho_sugerido}")

        return render_template("ia.html",
                               nicho_sugerido=nicho_sugerido,
                               lista_nichos=nichos_ativos)


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
@app.route('/login/', methods=['GET', 'POST']) # Adicione esta linha extra logo aci
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

@app.route("/auth/callback")
def auth_callback():
    try:
        code = request.args.get("code")
        
        if code:
            print(f"🎟️ Código de Autenticação detectado (?code={code[:6]}...). Trocando por sessão...")
            resposta = supabase.auth.exchange_code_for_session({"auth_code": code})
        else:
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
        
        if resposta and hasattr(resposta, 'user') and resposta.user:
            user = resposta.user
            
            session.permanent = True
            session["user_id"] = user.id
            session["email"] = user.email

            print(f"🌐 LOGIN SOCIAL GOOGLE DETERMINADO COM SUCESSO: {user.email}")

            try:
                checar_usuario = supabase.table("users").select("plano").eq("id", user.id).execute()
                if not checar_usuario.data:
                    supabase.table("users").insert({
                        "id": user.id,
                        "email": user.email,
                        "plano": "free",
                        "posts_limite": 10,
                        "posts_usados": 0
                    }).execute()
                    print(f"✅ Novo usuário Google criado com sucesso na tabela pública.")
                else:
                    supabase.table("users").update({
                        "email": user.email
                    }).eq("id", user.id).execute()
                    print(f"🔄 Usuário recorrente atualizado mantendo o plano original.")
            except Exception as table_err:
                print(f"⚠️ Nota de tabela na sincronização: {str(table_err)}")

            return redirect("/")
            
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
                print(f"✅ Usuário salvo na tabela pública 'users': {email}")
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
# GERADOR VALIDAR IMAGEM
# =========================

# Função para validar url da imagem
def validar_url_imagem(url):
    if not url:
        return False
    try:
        resposta = requests.head(url, timeout=5)
        return resposta.status_code == 200
    except:
        return False

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
            status_post = "pendente"
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
            # Valida URL da imagem, substitui se inválida
            IMAGEM_PADRAO = "https://coregov.com.br/static/imagem-padrao.png"
            if not validar_url_imagem(imagem_url):
                print("⚠️ URL da imagem inválida ou inacessível, usando imagem padrão.")
                imagem_url = IMAGEM_PADRAO
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
                print(f"Contador atualizado! Total usado: {novo_total}")
            flash("Postagem criada e enviada para agendamentos com sucesso!", "success")
            return redirect(url_for("ia"))
        except Exception as e:
            print("❌ EXCEÇÃO DISPARADA NO EXECUTOR IA:", str(e))
            flash(f"Ocorreu um erro interno no processo: {str(e)}", "error")
            return redirect(url_for("ia"))
    return render_template("ia.html")
# ... restante do app.py permanece igual 

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

# 🔒 PRESERVADO POR COMPLETO: ROTA DE CONFIGURAÇÕES ORIGINAL RESTAURADA
# 🔒 CORRIGIDO: ROTA DE CONFIGURAÇÕES COM SUPORTE A DADOS_USUARIO E USER NO HTML
@app.route("/configuracoes")
def configuracoes():
    if "user_id" not in session:
        return redirect("/login")
        
    try:
        # Puxa as infos do usuário logado na tabela pública do Supabase
        res = supabase.table("users").select("*").eq("id", session["user_id"]).execute()
        dados_usuario = res.data[0] if res.data else {}
        
        # Mapeamento dinâmico para os cards de conexões sociais e informações do formulário
        user_data = {
            "name": dados_usuario.get("display_name") or session.get("email", "").split("@")[0].capitalize(),
            "email": dados_usuario.get("email") or session.get("email"),
            "plan": (dados_usuario.get("plano") or "Free").upper(),
            "linkedin_connected": True if dados_usuario.get("linkedin_token") else False,
            "instagram_connected": True if dados_usuario.get("instagram_token") else False,
            "tipo_pix": dados_usuario.get("tipo_pix", ""),
            "chave_pix": dados_usuario.get("chave_pix", "")
        }
        
        # 🚀 SOLUÇÃO: Passando 'user' e também 'dados_usuario' para blindar o Jinja2
        return render_template("configuracoes.html", user=user_data, dados_usuario=dados_usuario)
    except Exception as e:
        print(f"❌ Erro ao carregar configurações: {str(e)}")
        # Fallback de segurança caso a tabela sofra timeout
        user_fallback = {
            "name": session.get("email", "").split("@")[0].capitalize(),
            "email": session.get("email"),
            "plan": "FREE",
            "linkedin_connected": False,
            "instagram_connected": False,
            "tipo_pix": "",
            "chave_pix": ""
        }
        return render_template("configuracoes.html", user=user_fallback, dados_usuario=user_fallback)
# 🔥 ADICIONADO SEM SOBREPOSIÇÃO: Endpoint para salvar os dados do PIX
@app.route("/configuracoes/salvar-pix", methods=["POST"])
def salvar_pix():
    if "user_id" not in session:
        return redirect("/login")
        
    tipo_pix = request.form.get("tipo_pix")
    chave_pix = request.form.get("chave_pix", "").strip()
    
    try:
        # Atualiza apenas os campos do PIX sem mexer em tokens ou logins
        supabase.table("users").update({
            "tipo_pix": tipo_pix,
            "chave_pix": chave_pix
        }).eq("id", session["user_id"]).execute()
        
        flash("Chave PIX atualizada com sucesso!", "success")
    except Exception as e:
        print(f"❌ Erro ao salvar PIX: {str(e)}")
        flash("Erro operacional ao salvar sua chave. Tente novamente.", "danger")
        
    return redirect("/configuracoes")


@app.route("/configuracoes/alterar-senha", methods=["POST"])
def alterar_senha():
    if "user_id" not in session:
        return redirect("/login")
        
    senha_atual = request.form.get("senha_atual")
    nova_senha = request.form.get("nova_senha")
    
    flash("Senha atualizada com sucesso! (Exemplo operacional)", "success")
    return redirect("/configuracoes")

# =========================
# GESTÃO FINANCEIRA: PLANOS E AFILIADOS
# =========================

@app.route("/planos")
def planos():
    if "user_id" not in session:
        return redirect("/login")
        
    try:
        # Busca as informações atualizadas do usuário logado (Plano, Posts Usados, etc.)
        usuario_res = supabase.table("users").select("*").eq("id", session["user_id"]).execute()
        
        if usuario_res.data:
            user_data = usuario_res.data[0]
        else:
            user_data = {}
            
        return render_template("planos.html", dados_usuario=user_data)
    except Exception as e:
        print(f"❌ Erro na rota de planos: {str(e)}")
        return redirect("/")
