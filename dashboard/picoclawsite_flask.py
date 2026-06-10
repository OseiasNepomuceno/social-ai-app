import os
import secrets
import random
import asyncio
import threading

from flask import (
    request,
    jsonify,
    render_template
)

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

from dashboard.monitor_editais import (
    buscar_editais_recentes_pncp,
    analisar_edital_com_deepseek,
)

CRON_SECRET = os.getenv("CRON_SECRET", "")

NICHOS_FALLBACK = [
    "Automação",
    "Dados",
    "Gestão",
    "Fiscal",
    "Produtividade",
    "Tecnologia",
    "Empreendedorismo",
    "Marketing Digital",
    "Finanças",
    "Recursos Humanos",
]


def buscar_nichos_tiktok(supabase):
    try:
        response = (
            supabase.table("nichos_tiktok")
            .select("nicho")
            .eq("ativo", True)
            .execute()
        )

        nichos = [
            row["nicho"]
            for row in response.data
            if row.get("nicho")
        ]

        if nichos:
            return nichos

        return NICHOS_FALLBACK

    except Exception as e:
        print(f"❌ ERRO ao buscar nichos: {e}")
        return NICHOS_FALLBACK


def salvar_conteudo(
    supabase,
    titulo,
    tipo,
    conteudo
):
    try:

        if not conteudo or len(conteudo.strip()) < 50:
            return {}

        response = (
            supabase.table("conteudos")
            .insert({
                "titulo": titulo,
                "tipo": tipo,
                "conteudo": conteudo.strip(),
                "status": "publicado"
            })
            .execute()
        )

        return response.data[0] if response.data else {}

    except Exception as e:
        print(f"❌ Erro ao salvar: {e}")
        return {}


async def sugerir_temas_automaticos(nichos):
    nichos_sorteados = random.sample(
        nichos,
        min(3, len(nichos))
    )

    prompt = f"""Você é um especialista em conteúdo para redes sociais voltado ao mercado empresarial e de gestão.

Nichos: {', '.join(nichos_sorteados)}

Responda APENAS neste formato:
NICHO: tema sugerido"""

    resultado = chamar_picoclaw(
        prompt,
        timeout=60
    )

    if not resultado.get("success"):
        return []

    temas = []

    for linha in resultado["conteudo"].split("\n"):
        if ":" in linha:
            partes = linha.split(":", 1)

            nicho = partes[0].strip()
            tema = partes[1].strip()

            if nicho and tema:
                temas.append({
                    "tema": tema,
                    "nicho": nicho,
                    "duracao": 60
                })

    return temas



def registrar_rotas_picoclaw(app, supabase):

           @app.route(
        "/interno/gerar-automatico",
        methods=["POST"]
    )
    
    def gerar_conteudo_automatico():

        token = request.headers.get(
            "X-Cron-Token",
            ""
        )

        if (
            not CRON_SECRET
            or
            not secrets.compare_digest(
                token,
                CRON_SECRET
            )
        ):

            return jsonify({
                "erro": "Não autorizado"
            }), 401

        nichos = buscar_nichos_tiktok(
            supabase
        )

        threading.Thread(
            target=lambda:
                asyncio.run(
                    _processar_conteudo_background(
                        supabase,
                        nichos
                    )
                ),
            daemon=True
        ).start()

        return jsonify({
            "status": "aceito",
            "mensagem":
                "Processamento iniciado",
            "nichos":
                len(nichos)
        }), 202



    def picoclaw_status():

        nichos = buscar_nichos_tiktok(
            supabase
        )

        return jsonify({
            "status": "online",
            "modelo": "picoclaw",
            "nichos_tiktok": nichos,
            "total_nichos": len(nichos)
        })


    @app.route("/monitor-editais")
    def pagina_monitor_editais():

        return render_template(
            "editais.html"
        )


    @app.route("/posts")
    def listar_posts():

        response = (
            supabase.table("conteudos")
            .select("*")
            .eq("tipo", "post")
            .eq("status", "publicado")
            .execute()
        )

        return render_template(
            "posts.html",
            posts=response.data
        )


    @app.route("/roteiros-tiktok")
    def listar_roteiros():

        response = (
            supabase.table("conteudos")
            .select("*")
            .eq("tipo", "roteiro_tiktok")
            .eq("status", "publicado")
            .execute()
        )

        return render_template(
            "roteiros.html",
            roteiros=response.data
        )


    @app.route("/ctas")
    def listar_ctas():

        response = (
            supabase.table("conteudos")
            .select("*")
            .eq("tipo", "cta")
            .eq("status", "publicado")
            .execute()
        )

        return render_template(
            "ctas.html",
            ctas=response.data
        )


    @app.route("/e-books")
    def listar_ebooks():

        response = (
            supabase.table("conteudos")
            .select("*")
            .eq("tipo", "ebook")
            .eq("status", "publicado")
            .execute()
        )

        return render_template(
            "e-books.html",
            ebooks=response.data
        )


    @app.route("/infograficos")
    def listar_infograficos():

        response = (
            supabase.table("conteudos")
            .select("*")
            .eq("tipo", "infografico")
            .eq("status", "publicado")
            .execute()
        )

        return render_template(
            "infografico.html",
            infograficos=response.data
        )

            @app.route(
        "/gerar/monitorar-editais",
        methods=["POST"]
    )
    def endpoint_monitorar_editais_manual():

        body = request.get_json(force=True)

        nicho = body.get(
            "nicho",
            "Tecnologia e Automação"
        )

        dias = body.get(
            "dias",
            1
        )

        editais_encontrados = (
            buscar_editais_recentes_pncp(
                dias_atras=dias
            )
        )

        if not editais_encontrados:

            return jsonify({
                "status": "vazio",
                "mensagem": (
                    "Nenhum edital encontrado."
                )
            })

        oportunidades = []

        for edital in editais_encontrados:

            analise = (
                analisar_edital_com_deepseek(
                    edital,
                    nicho_cliente=nicho
                )
            )

            if (
                analise and
                analise.get("decisao")
                == "RECOMENDADO"
            ):

                oportunidades.append(
                    analise
                )

        return jsonify({
            "status": "sucesso",
            "total_analisado":
                len(editais_encontrados),
            "total_recomendado":
                len(oportunidades),
            "dados":
                oportunidades
        })


    @app.route(
        "/gerar/post",
        methods=["POST"]
    )
    def endpoint_gerar_post():

        body = request.get_json(force=True)

        tema = body.get("tema")
        rede = body.get(
            "rede",
            "LinkedIn"
        )

        modo = body.get(
            "modo",
            "engajamento"
        )

        nicho = body.get(
            "nicho",
            ""
        )

        nicho = (
            nicho or
            inferir_nicho(
                tema,
                NICHOS_FALLBACK
            )
        )

        resultado = gerar_post(
            tema,
            rede,
            modo,
            nicho
        )

        if not resultado.get("success"):

            return jsonify({
                "status": "erro",
                "erro":
                    resultado.get("erro")
            }), 500

        salvo = salvar_conteudo(
            supabase,
            tema,
            "post",
            resultado["conteudo"]
        )

        return jsonify({
            "status": "ok",
            "nicho": nicho,
            "conteudo":
                resultado["conteudo"],
            "salvo": salvo
        })


    @app.route(
        "/gerar/roteiro-tiktok",
        methods=["POST"]
    )
    def endpoint_gerar_roteiro():

        body = request.get_json(force=True)

        tema = body.get("tema")
        nicho = body.get("nicho", "")
        duracao = body.get("duracao", 60)

        nicho = (
            nicho or
            inferir_nicho(
                tema,
                NICHOS_FALLBACK
            )
        )

        resultado = gerar_roteiro_tiktok(
            tema,
            nicho,
            duracao
        )

        if not resultado.get("success"):
            return jsonify({
                "status": "erro",
                "erro": resultado.get("erro")
            }), 500

        salvo = salvar_conteudo(
            supabase,
            tema,
            "roteiro_tiktok",
            resultado["conteudo"]
        )

        return jsonify({
            "status": "ok",
            "nicho": nicho,
            "conteudo": resultado["conteudo"],
            "salvo": salvo
        })


    @app.route(
        "/gerar/cta",
        methods=["POST"]
    )
    def endpoint_gerar_cta():

        body = request.get_json(force=True)

        tema = body.get("tema")
        nicho = body.get("nicho", "")
        objetivo = body.get("objetivo", "conversão")
        canal = body.get("canal", "site")

        nicho = (
            nicho or
            inferir_nicho(
                tema,
                NICHOS_FALLBACK
            )
        )

        resultado = gerar_cta(
            tema,
            nicho,
            objetivo,
            canal
        )

        if not resultado.get("success"):
            return jsonify({
                "status": "erro",
                "erro": resultado.get("erro")
            }), 500

        salvo = salvar_conteudo(
            supabase,
            tema,
            "cta",
            resultado["conteudo"]
        )

        return jsonify({
            "status": "ok",
            "nicho": nicho,
            "conteudo": resultado["conteudo"],
            "salvo": salvo
        })


    @app.route(
        "/gerar/ebook",
        methods=["POST"]
    )
    def endpoint_gerar_ebook():

        body = request.get_json(force=True)

        tema = body.get("tema")
        nicho = body.get("nicho", "")
        publico_alvo = body.get(
            "publico_alvo",
            "gestores e empresários"
        )

        num_capitulos = body.get(
            "num_capitulos",
            5
        )

        nicho = (
            nicho or
            inferir_nicho(
                tema,
                NICHOS_FALLBACK
            )
        )

        resultado = gerar_ebook(
            tema,
            nicho,
            publico_alvo,
            num_capitulos
        )

        if not resultado.get("success"):
            return jsonify({
                "status": "erro",
                "erro": resultado.get("erro")
            }), 500

        salvo = salvar_conteudo(
            supabase,
            tema,
            "ebook",
            resultado["conteudo"]
        )

        return jsonify({
            "status": "ok",
            "nicho": nicho,
            "conteudo": resultado["conteudo"],
            "salvo": salvo
        })        


    @app.route(
        "/gerar/infografico",
        methods=["POST"]
    )
    def endpoint_gerar_infografico():

        body = request.get_json(force=True)

        tema = body.get("tema")
        nicho = body.get("nicho", "")
        formato = body.get("formato", "lista")

        nicho = (
            nicho or
            inferir_nicho(
                tema,
                NICHOS_FALLBACK
            )
        )

        resultado = gerar_infografico(
            tema,
            nicho,
            formato
        )

        if not resultado.get("success"):
            return jsonify({
                "status": "erro",
                "erro": resultado.get("erro")
            }), 500

        salvo = salvar_conteudo(
            supabase,
            tema,
            "infografico",
            resultado["conteudo"]
        )

        return jsonify({
            "status": "ok",
            "nicho": nicho,
            "conteudo": resultado["conteudo"],
            "salvo": salvo
        })


    @app.route(
        "/gerar/template",
        methods=["POST"]
    )
    def endpoint_gerar_template():

        body = request.get_json(force=True)

        tema = body.get("tema")
        nicho = body.get("nicho", "")
        tipo = body.get("tipo", "post")

        nicho = (
            nicho or
            inferir_nicho(
                tema,
                NICHOS_FALLBACK
            )
        )

        resultado = gerar_template(
            tipo,
            nicho,
            tema
        )

        if not resultado.get("success"):
            return jsonify({
                "status": "erro",
                "erro": resultado.get("erro")
            }), 500

        salvo = salvar_conteudo(
            supabase,
            tema,
            "template",
            resultado["conteudo"]
        )

        return jsonify({
            "status": "ok",
            "nicho": nicho,
            "conteudo": resultado["conteudo"],
            "salvo": salvo
        })


async def _processar_conteudo_background(
    supabase,
    nichos
):
    temas = await sugerir_temas_automaticos(
        nichos
    )

    if not temas:
        return

    for item in temas:

        tema = item["tema"]
        nicho = item["nicho"]

        try:

            r = gerar_roteiro_tiktok(
                tema,
                nicho,
                item["duracao"]
            )

            if r.get("success"):
                salvar_conteudo(
                    supabase,
                    tema,
                    "roteiro_tiktok",
                    r["conteudo"]
                )

        except Exception as e:
            print(e)

        try:

            r = gerar_post(
                tema,
                "LinkedIn",
                "engajamento",
                nicho
            )

            if r.get("success"):
                salvar_conteudo(
                    supabase,
                    tema,
                    "post",
                    r["conteudo"]
                )

        except Exception as e:
            print(e)

        try:

            r = gerar_cta(
                tema,
                nicho,
                "conversão",
                "site"
            )

            if r.get("success"):
                salvar_conteudo(
                    supabase,
                    tema,
                    "cta",
                    r["conteudo"]
                )

        except Exception as e:
            print(e)



        





