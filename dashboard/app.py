@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]

        try:
            # Envia dados para o serviço Auth do Supabase
            resposta = supabase.auth.sign_up({
                "email": email,
                "password": senha
            })
            
            user = resposta.user
            
            # 💡 CASO EXIJA CONFIRMAÇÃO POR E-MAIL (Aviso customizado e otimizado):
            if not user or not hasattr(user, 'id') or user.id is None:
                print("⚠️ Pré-cadastro efetuado. Aguardando validação de e-mail.")
                return render_template(
                    "register.html", 
                    sucesso="📬 Quase lá! Enviamos um e-mail de ativação para você. Acesse sua caixa de entrada (ou spam) e clique no link de validação. Assim que confirmar, seu acesso será liberado na hora! 🚀"
                )

            # Se o Supabase estiver configurado para auto-confirmar, insere direto
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

            print(f"✅ USUÁRIO CRIADO E SALVO: {email}")
            return redirect("/")

        except Exception as e:
            error_msg = str(e)
            print(f"❌ REGISTER ERROR CAPTURADO: {error_msg}")
            
            if "User already registered" in error_msg or "already exists" in error_msg:
                user_friendly_error = "Este e-mail já está cadastrado no sistema. Tente fazer login."
            elif "should be at least" in error_msg:
                user_friendly_error = "A senha escolhida é muito curta. Utilize pelo menos 6 caracteres."
            else:
                user_friendly_error = "Houve uma instabilidade temporária ao salvar seus dados. Verifique suas informações e tente novamente."
                
            return render_template("register.html", erro=user_friendly_error)

    return render_template("register.html")
