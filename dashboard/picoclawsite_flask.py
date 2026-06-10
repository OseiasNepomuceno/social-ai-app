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




