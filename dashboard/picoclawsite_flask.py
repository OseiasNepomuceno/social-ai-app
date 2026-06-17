import os
import secrets
import random
import asyncio
import threading
from datetime import datetime
from flask import request, jsonify, render_template
from dashboard.picoclaw_agent import (
    gerar_post,
    gerar_roteiro_tiktok,
    gerar_cta,
    gerar_ebook,
    gerar_infografico,
    gerar_template,
    inferir_nicho,
    chamar_picoclaw,
)

CRON_SECRET = os.getenv("CRON_SECRET", "")
NICHOS_FALLBACK = [
    "Automação", "Dados", "Gestão", "Fiscal", "Produtividade",
    "Tecnologia", "Empreendedorismo", "Marketing Digital", "Finanças", "Recursos Humanos",
]

def buscar_nichos_tiktok(supabase):
    try:
        response = supabase.table("nichos_tiktok").select("nicho").eq("ativo", True).execute()
        nichos = [row["nicho"] for row in response.data if row.get("nicho")]
        return nichos if nichos else NICHOS_FALLBACK
    except Exception as e:
        print(f"❌ ERRO ao buscar nichos: {e}")
        return NICHOS_FALLBACK

def salvar_conteudo(supabase, titulo, tipo, conteudo, categoria="gratuito"):
    try:
        if not conteudo or len(conteudo.strip()) < 50:
            return {}
        response = supabase.table("conteudos").insert({
            "titulo": titulo,
            "tipo": tipo,
            "conteudo": conteudo.strip(),
            "status": "publicado",
            "categoria": categoria
        }).execute()
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"❌ Erro ao salvar: {e}")
        return {}

async def sugerir_temas_automaticos(nichos):
    nichos_sorteados = random.sample(nichos, min(3, len(nichos)))
    prompt = f"""Você é um especialista em conteúdo para redes sociais voltado ao mercado empresarial e de gestão.
Nichos: {', '.join(nichos_sorteados)}
Responda APENAS neste formato:
NICHO: tema sugerido"""
    
    resultado = chamar_picoclaw(prompt, timeout=60)
    if not resultado.get("success"):
        return []
    
    temas = []
    for linha in resultado["conteudo"].split("\n"):
        if ":" in linha:
            partes = linha.split(":", 1)
            nicho = partes[0].strip()
            tema = partes[1].strip()
            if nicho and tema:
                temas.append({"tema": tema, "nicho": nicho, "duracao": 60})
    return temas

def registrar_rotas_picoclaw(app, supabase):

    @app.route("/interno/gerar-automatico", methods=["POST"])
    def gerar_conteudo_automatico():
        token = request.headers.get("X-Cron-Token", "")
        if not CRON_SECRET or not secrets.compare_digest(token, CRON_SECRET):
            return jsonify({"erro": "Não autorizado"}), 401
        
        nichos = buscar_nichos_tiktok(supabase)
        threading.Thread(
            target=lambda: asyncio.run(_processar_conteudo_background(supabase, nichos)),
            daemon=True
        ).start()
        return jsonify({"status": "aceito", "mensagem": "Processamento iniciado", "nichos": len(nichos)}), 202

    @app.route("/picoclaw/status")
    def picoclaw_status():
        nichos = buscar_nichos_tiktok(supabase)
        return jsonify({
            "status": "online",
            "modelo": "picoclaw",
            "nichos_tiktok": nichos,
            "total_nichos": len(nichos)
        })

    @app.route("/monitor-editais")
    def pagina_monitor_editais():
        return render_template("editais.html")

    @app.route("/api/oportunidades-analisadas", methods=["GET"])
    def listar_oportunidades():
        try:
            response = supabase.table("oportunidades_analisadas").select("*").order("data_analise", desc=True).execute()
            return jsonify({"status": "ok", "total": len(response.data), "oportunidades": response.data})
        except Exception as e:
            print(f"❌ Erro ao listar oportunidades: {e}")
            return jsonify({"status": "erro", "erro": str(e)}), 500

    @app.route("/posts")
    def listar_posts():
        response = supabase.table("conteudos").select("*").eq("tipo", "post").eq("status", "publicado").execute()
        return render_template("posts.html", posts=response.data)

    @app.route("/roteiros-tiktok")
    def listar_roteiros():
        response = supabase.table("conteudos").select("*").eq("tipo", "roteiro_tiktok").eq("status", "publicado").execute()
        return render_template("roteiros.html", roteiros=response.data)

    @app.route("/ctas")
    def listar_ctas():
        response = supabase.table("conteudos").select("*").eq("tipo", "cta").eq("status", "publicado").execute()
        return render_template("ctas.html", ctas=response.data)

    @app.route("/e-books")
    def listar_ebooks():
        response = supabase.table("conteudos").select("*").eq("tipo", "ebook").eq("status", "publicado").execute()
        return render_template("e-books.html", ebooks=response.data)

    @app.route("/infograficos")
    def listar_infograficos():
        response = supabase.table("conteudos").select("*").eq("tipo", "infografico").eq("status", "publicado").execute()
        return render_template("infografico.html", infograficos=response.data)

    @app.route("/gerar/monitorar-editais", methods=["POST"])
    def endpoint_monitorar_editais_manual():
        body = request.get_json(force=True)
        nicho = body.get("nicho", "Todos os Nichos")
        dias = body.get("dias", 1)
        buscar_privadas = body.get("buscar_privadas", True)
        dias_efetivos = max(1, dias * 30)

        def processar_editais():
            try:
                print(f"🚀 Iniciando varredura de oportunidades para nicho: {nicho}")
                oportunidades_salvas = []
                
                print("📊 Fase 1: Buscando editais do governo (PNCP)...")
                from dashboard.monitor_editais import (
                    buscar_editais_recentes_pncp,
                    analisar_oportunidade_com_picoclaw,
                    buscar_oportunidades_privadas
                )
                
                editais_governo = buscar_editais_recentes_pncp(dias_atras=dias_efetivos)
                print(f"✅ {len(editais_governo)} editais do governo encontrados")
                
                editais_privados = []
                if buscar_privadas:
                    print("💼 Fase 2: Buscando oportunidades privadas...")
                    editais_privados = buscar_oportunidades_privadas(dias_atras=dias_efetivos)
                    print(f"✅ {len(editais_privados)} oportunidades privadas encontradas")
                
                todas_oportunidades = editais_governo + editais_privados
                print(f"📈 Total: {len(todas_oportunidades)} oportunidades")
                
                if len(todas_oportunidades) == 0:
                    print("⚠️ Nenhuma oportunidade encontrada no período especificado")
                    from dashboard.telegram_alerts import enviar_alerta
                    enviar_alerta(f"⚠️ Varredura com 0 resultados para nicho: {nicho}", emoji="⚠️")
                    return
                
                print(f"🔍 Fase 3: Analisando e registrando todas as oportunidades...")
                
                for idx, oportunidade in enumerate(todas_oportunidades, 1):
                    try:
                        print(f"  [{idx}/{len(todas_oportunidades)}] Registrando: {oportunidade['orgao']}")
                        analise = analisar_oportunidade_com_picoclaw(oportunidade, nicho_cliente=nicho)
                        
                        if not analise:
                            analise = {
                                "orgao": oportunidade['orgao'],
                                "valor": oportunidade.get("valor_estimado"),
                                "tipo": oportunidade.get("tipo"),
                                "fonte": oportunidade.get("fonte"),
                                "link": oportunidade.get("link"),
                                "relevancia": "ANÁLISE_NÃO_DISPONÍVEL",
                                "motivo": "Sistema não conseguiu analisar",
                                "proximos_passos": "Verificar manualmente"
                            }
                        
                        dados_salvar = {
                            "orgao": analise.get("orgao", oportunidade['orgao']),
                            "objeto": oportunidade.get("objeto"),
                            "valor_estimado": str(analise.get("valor", "N/A")),
                            "tipo": analise.get("tipo", "misto"),
                            "fonte": analise.get("fonte", "Múltiplas"),
                            "relevancia": analise.get("relevancia", "ANÁLISE_PENDENTE"),
                            "motivo_analise": analise.get("motivo", ""),
                            "proximos_passos": analise.get("proximos_passos", ""),
                            "link": analise.get("link", oportunidade.get("link")),
                            "nicho_cliente": nicho,
                            "data_analise": datetime.now().isoformat()
                        }
                        
                        response = supabase.table("oportunidades_analisadas").insert(dados_salvar).execute()
                        if response.data:
                            oportunidades_salvas.append(dados_salvar)
                            print(f"  ✅ Registrada")
                        
                    except Exception as e:
                        print(f"  ⚠️ Erro: {e}")
                        try:
                            dados_salvar = {
                                "orgao": oportunidade['orgao'],
                                "objeto": oportunidade.get("objeto"),
                                "valor_estimado": str(oportunidade.get("valor_estimado", "N/A")),
                                "tipo": oportunidade.get("tipo", "desconhecido"),
                                "fonte": oportunidade.get("fonte", "Varredura"),
                                "relevancia": "ERRO_NA_ANÁLISE",
                                "motivo_analise": str(e),
                                "proximos_passos": "Revisar manualmente",
                                "link": oportunidade.get("link"),
                                "nicho_cliente": nicho,
                                "data_analise": datetime.now().isoformat()
                            }
                            supabase.table("oportunidades_analisadas").insert(dados_salvar).execute()
                            oportunidades_salvas.append(dados_salvar)
                        except:
                            pass
                
                print(f"\n{'='*60}")
                print(f"🎯 RESUMO DA VARREDURA")
                print(f"{'='*60}")
                print(f"Total analisado: {len(todas_oportunidades)}")
                print(f"Total registrado: {len(oportunidades_salvas)}")
                print(f"Período: {dias_efetivos} dias")
                print(f"Nicho: {nicho}")
                print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                print(f"{'='*60}")
                
                if oportunidades_salvas:
                    from dashboard.telegram_alerts import enviar_alerta
                    mensagem = f"""
✅ VARREDURA COMPLETA - {len(oportunidades_salvas)} oportunidades registradas

Nicho: {nicho}
Período: {dias_efetivos} dias
Total: {len(todas_oportunidades)}
Governo: {len(editais_governo)}
Privado: {len(editais_privados)}

Acesse o painel para revisar todas as oportunidades.
"""
                    enviar_alerta(mensagem, emoji="🎯")
                
            except Exception as e:
                print(f"❌ Erro crítico: {e}")
                from dashboard.telegram_alerts import enviar_alerta
                enviar_alerta(f"❌ Erro na varredura: {str(e)}", emoji="🔴")

        thread = threading.Thread(target=processar_editais, daemon=True)
        thread.start()

        return jsonify({
            "status": "processando",
            "mensagem": "Varredura iniciada em background",
            "timestamp": datetime.now().isoformat()
        }), 202

    @app.route("/gerar/post", methods=["POST"])
    def endpoint_gerar_post():
        body = request.get_json(force=True)
        tema = body.get("tema")
        rede = body.get("rede", "LinkedIn")
        modo = body.get("modo", "engajamento")
        nicho = body.get("nicho", "")

        nicho = nicho or inferir_nicho(tema, NICHOS_FALLBACK)
        resultado = gerar_post(tema, rede, modo, nicho)

        if not resultado.get("success"):
            return jsonify({"status": "erro", "erro": resultado.get("erro")}), 500

        salvo = salvar_conteudo(supabase, tema, "post", resultado["conteudo"])
        return jsonify({"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo})

    @app.route("/gerar/roteiro-tiktok", methods=["POST"])
    def endpoint_gerar_roteiro():
        body = request.get_json(force=True)
        tema = body.get("tema")
        nicho = body.get("nicho", "")
        duracao = body.get("duracao", 60)

        nicho = nicho or inferir_nicho(tema, NICHOS_FALLBACK)
        resultado = gerar_roteiro_tiktok(tema, nicho, duracao)

        if not resultado.get("success"):
            return jsonify({"status": "erro", "erro": resultado.get("erro")}), 500

        salvo = salvar_conteudo(supabase, tema, "roteiro_tiktok", resultado["conteudo"])
        return jsonify({"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo})

    @app.route("/gerar/cta", methods=["POST"])
    def endpoint_gerar_cta():
        body = request.get_json(force=True)
        tema = body.get("tema")
        nicho = body.get("nicho", "")
        objetivo = body.get("objetivo", "conversão")
        canal = body.get("canal", "site")

        nicho = nicho or inferir_nicho(tema, NICHOS_FALLBACK)
        resultado = gerar_cta(tema, nicho, objetivo, canal)

        if not resultado.get("success"):
            return jsonify({"status": "erro", "erro": resultado.get("erro")}), 500

        salvo = salvar_conteudo(supabase, tema, "cta", resultado["conteudo"])
        return jsonify({"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo})

    @app.route("/gerar/ebook", methods=["POST"])
    def endpoint_gerar_ebook():
        body = request.get_json(force=True)
        tema = body.get("tema")
        nicho = body.get("nicho", "")
        publico_alvo = body.get("publico_alvo", "gestores e empresários")
        num_capitulos = body.get("num_capitulos", 5)

        nicho = nicho or inferir_nicho(tema, NICHOS_FALLBACK)
        resultado = gerar_ebook(tema, nicho, publico_alvo, num_capitulos)

        if not resultado.get("success"):
            return jsonify({"status": "erro", "erro": resultado.get("erro")}), 500

        salvo = salvar_conteudo(supabase, tema, "ebook", resultado["conteudo"])
        return jsonify({"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo})

    @app.route("/gerar/infografico", methods=["POST"])
    def endpoint_gerar_infografico():
        body = request.get_json(force=True)
        tema = body.get("tema")
        nicho = body.get("nicho", "")
        formato = body.get("formato", "lista")

        nicho = nicho or inferir_nicho(tema, NICHOS_FALLBACK)
        resultado = gerar_infografico(tema, nicho, formato)

        if not resultado.get("success"):
            return jsonify({"status": "erro", "erro": resultado.get("erro")}), 500

        salvo = salvar_conteudo(supabase, tema, "infografico", resultado["conteudo"])
        return jsonify({"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo})

    @app.route("/gerar/template", methods=["POST"])
    def endpoint_gerar_template():
        body = request.get_json(force=True)
        tema = body.get("tema")
        nicho = body.get("nicho", "")
        tipo = body.get("tipo", "post")

        nicho = nicho or inferir_nicho(tema, NICHOS_FALLBACK)
        resultado = gerar_template(tipo, nicho, tema)

        if not resultado.get("success"):
            return jsonify({"status": "erro", "erro": resultado.get("erro")}), 500

        salvo = salvar_conteudo(supabase, tema, "template", resultado["conteudo"])
        return jsonify({"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo})


async def _processar_conteudo_background(supabase, nichos):
    temas = await sugerir_temas_automaticos(nichos)
    if not temas:
        return

    for item in temas:
        tema = item["tema"]
        nicho = item["nicho"]

        try:
            r = gerar_roteiro_tiktok(tema, nicho, item["duracao"])
            if r.get("success"):
                salvar_conteudo(supabase, tema, "roteiro_tiktok", r["conteudo"])
        except Exception as e:
            print(f"❌ Erro ao gerar roteiro: {e}")

        try:
            r = gerar_post(tema, "LinkedIn", "engajamento", nicho)
            if r.get("success"):
                salvar_conteudo(supabase, tema, "post", r["conteudo"])
        except Exception as e:
            print(f"❌ Erro ao gerar post: {e}")

        try:
            r = gerar_cta(tema, nicho, "conversão", "site")
            if r.get("success"):
                salvar_conteudo(supabase, tema, "cta", r["conteudo"])
        except Exception as e:
            print(f"❌ Erro ao gerar CTA: {e}")
