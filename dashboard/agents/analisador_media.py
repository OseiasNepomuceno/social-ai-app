import os
from supabase import create_client

# =========================
# ENV
# =========================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🎯 LISTA ATUALIZADA: Incluindo os 4 novos nichos para monitoramento em tempo real
NICHOS_ALVO = [
    "marketing", 
    "tecnologia", 
    "negocios", 
    "financeiro", 
    "vendas", 
    "empreendedorismo",
    "contabilidade",
    "psicologia",
    "engenharia",
    "saude"
]
ORIGENS_ALVO = ["pixabay", "pexels", "desconhecida"]

# =========================
# VERIFICAR TOTAL E ORIGEM
# =========================

def verificar_total_imagens():
    """
    Verifica o total real de imagens coletadas e filtra por origem
    usando agregações rápidas do Supabase.
    """
    try:
        print("\n" + "="*50)
        print("📊 ANÁLISE DE IMAGENS COLETADAS")
        print("="*50)

        # Total geral ultra rápido
        resposta_total = supabase.table("media_library").select("*", count="exact").limit(1).execute()
        total_geral = resposta_total.count if resposta_total.count is not None else 0

        print(f"\n📸 TOTAL GERAL NO BANCO: {total_geral:,} imagens")

        print("\n" + "="*50)
        print("🏠 IMAGENS POR ORIGEM")
        print("="*50)

        origem_counts = {}
        for origem in ORIGENS_ALVO:
            res = supabase.table("media_library").select("*", count="exact").eq("origem", origem).limit(1).execute()
            if res.count and res.count > 0:
                origem_counts[origem] = res.count
                print(f"  {origem}: {res.count:,}")
        
        return total_geral, origem_counts

    except Exception as e:
        print(f"❌ ERRO TOTAL/ORIGEM: {str(e)}")
        return 0, {}

# =========================
# VERIFICAR IMAGENS POR NICHO
# =========================

def verificar_imagens_por_nicho(total_geral):
    """
    Verifica quantas imagens foram coletadas para cada nicho real
    usando contagem exata por agrupamento lógico.
    """
    try:
        print("\n" + "="*50)
        print("🎯 IMAGENS POR NICHO")
        print("="*50)

        nicho_counts = {}
        
        for nicho in NICHOS_ALVO:
            # Conta exatamente quantas linhas possuem o nicho específico
            res = supabase.table("media_library").select("*", count="exact").eq("nicho", nicho).limit(1).execute()
            count = res.count if res.count is not None else 0
            nicho_counts[nicho] = count

            percentual = (count / total_geral * 100) if total_geral > 0 else 0
            print(f"  📷 {nicho.upper()}: {count:,} ({percentual:.1f}%)")

        return nicho_counts

    except Exception as e:
        print(f"❌ ERRO NICHO: {str(e)}")
        return {}

# =========================
# VERIFICAR IMAGENS ATIVAS
# =========================

def verificar_imagens_ativas():
    """
    Verifica a proporção de imagens ativas e inativas.
    """
    try:
        print("\n" + "="*50)
        print("✅ STATUS DAS IMAGENS")
        print("="*50)

        ativas = supabase.table("media_library").select("*", count="exact").eq("ativo", True).limit(1).execute()
        inativas = supabase.table("media_library").select("*", count="exact").eq("ativo", False).limit(1).execute()

        total_ativas = ativas.count if ativas.count is not None else 0
        total_inativas = inativas.count if inativas.count is not None else 0
        total = total_ativas + total_inativas

        print(f"\n  ✅ Ativas: {total_ativas:,}")
        print(f"  ❌ Inativas: {total_inativas:,}")
        print(f"  📊 Total: {total:,}")

        if total > 0:
            pct_ativas = (total_ativas / total) * 100
            print(f"  📈 Taxa de atividade: {pct_ativas:.1f}%")

        return total_ativas, total_inativas

    except Exception as e:
        print(f"❌ ERRO STATUS: {str(e)}")
        return 0, 0

# =========================
# RELATÓRIO COMPLETO
# =========================

def gerar_relatorio_completo():
    """
    Gera a carga de dados unificada consumida pela rota Flask.
    """
    print("\n" + "="*60)
    print("🔍 RELATÓRIO COMPLETO DE MÍDIA")
    print("="*60)

    total_geral, origem_counts = verificar_total_imagens()
    nicho_counts = verificar_imagens_por_nicho(total_geral)
    ativas, inativas = verificar_imagens_ativas()

    print("\n" + "="*60)
    print("💡 RECOMENDAÇÕES")
    print("="*60)

    if nicho_counts:
        nichos_baixos = [(n, c) for n, c in nicho_counts.items() if c < 500]
        if nichos_baixos:
            print("\n⚠️ Nichos precisando de atenção (<500 imagens):")
            for nicho, count in nichos_baixos:
                print(f"  - {nicho}: apenas {count:,}")

        nichos_altos = [(n, c) for n, c in nicho_counts.items() if c >= 5000]
        if nichos_altos:
            print("\n✅ Nichos robustos (>5.000 imagens):")
            for nicho, count in nichos_altos:
                print(f"  - {nicho}: {count:,}")

    print("\n" + "="*60 + "\n")

    return {
        "total": total_geral,
        "por_nicho": nicho_counts,
        "por_origem": origem_counts,
        "ativas": ativas,
        "inativas": inativas
    }

if __name__ == "__main__":
    relatorio = gerar_relatorio_completo()
