import os
from supabase import create_client

# =========================
# ENV
# =========================

SUPABASE_URL = os.getenv(
    "SUPABASE_URL"
)

SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY"
)

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# =========================
# VERIFICAR TOTAL DE IMAGENS
# =========================

def verificar_total_imagens():
    """
    Verifica o total de imagens coletadas
    no Supabase (tabela media_library)
    """
    
    try:

        print("\n" + "="*50)
        print("📊 ANÁLISE DE IMAGENS COLETADAS")
        print("="*50)

        # Total geral
        resposta_total = supabase.table(
            "media_library"
        ).select(
            "count",
            count="exact"
        ).execute()

        total_geral = resposta_total.count

        print(f"\n📸 TOTAL GERAL: {total_geral:,} imagens")

        # Por origem
        print("\n" + "="*50)
        print("🏠 IMAGENS POR ORIGEM")
        print("="*50)

        origens = supabase.table(
            "media_library"
        ).select(
            "origem"
        ).execute()

        origem_counts = {}

        for item in origens.data:

            origem = item.get("origem", "desconhecida")

            origem_counts[origem] = (
                origem_counts.get(origem, 0) + 1
            )

        for origem, count in sorted(
            origem_counts.items(),
            key=lambda x: x[1],
            reverse=True
        ):

            print(f"  {origem}: {count:,}")

        return total_geral, origem_counts

    except Exception as e:

        print(f"❌ ERRO: {str(e)}")

        return None, None

# =========================
# VERIFICAR IMAGENS POR NICHO
# =========================

def verificar_imagens_por_nicho():
    """
    Verifica quantas imagens foram coletadas
    para cada nicho
    """
    
    try:

        print("\n" + "="*50)
        print("🎯 IMAGENS POR NICHO")
        print("="*50)

        # Buscar todas as imagens
        resposta = supabase.table(
            "media_library"
        ).select(
            "nicho"
        ).execute()

        nicho_counts = {}

        for item in resposta.data:

            nicho = item.get("nicho", "desconhecido")

            nicho_counts[nicho] = (
                nicho_counts.get(nicho, 0) + 1
            )

        # Exibir resultados ordenados
        print()

        for nicho, count in sorted(
            nicho_counts.items(),
            key=lambda x: x[1],
            reverse=True
        ):

            percentual = (
                (count / len(resposta.data)) * 100
                if resposta.data else 0
            )

            print(
                f"  📷 {nicho.upper()}: "
                f"{count:,} ({percentual:.1f}%)"
            )

        return nicho_counts

    except Exception as e:

        print(f"❌ ERRO: {str(e)}")

        return None

# =========================
# VERIFICAR IMAGENS ATIVAS
# =========================

def verificar_imagens_ativas():
    """
    Verifica quantas imagens estão ativas
    """
    
    try:

        print("\n" + "="*50)
        print("✅ STATUS DAS IMAGENS")
        print("="*50)

        ativas = supabase.table(
            "media_library"
        ).select(
            "count",
            count="exact"
        ).eq(
            "ativo",
            True
        ).execute()

        inativas = supabase.table(
            "media_library"
        ).select(
            "count",
            count="exact"
        ).eq(
            "ativo",
            False
        ).execute()

        total_ativas = ativas.count

        total_inativas = inativas.count

        total = total_ativas + total_inativas

        print(f"\n  ✅ Ativas: {total_ativas:,}")
        print(f"  ❌ Inativas: {total_inativas:,}")
        print(f"  📊 Total: {total:,}")

        if total > 0:

            pct_ativas = (
                (total_ativas / total) * 100
            )

            print(
                f"  📈 Taxa de atividade: "
                f"{pct_ativas:.1f}%"
            )

        return total_ativas, total_inativas

    except Exception as e:

        print(f"❌ ERRO: {str(e)}")

        return None, None

# =========================
# RELATÓRIO COMPLETO
# =========================

def gerar_relatorio_completo():
    """
    Gera um relatório completo de todas
    as imagens coletadas
    """
    
    print("\n" + "="*60)
    print("🔍 RELATÓRIO COMPLETO DE MÍDIA")
    print("="*60)

    total_geral, origem_counts = (
        verificar_total_imagens()
    )

    nicho_counts = verificar_imagens_por_nicho()

    ativas, inativas = verificar_imagens_ativas()

    # Recomendações
    print("\n" + "="*60)
    print("💡 RECOMENDAÇÕES")
    print("="*60)

    if nicho_counts:

        nichos_baixos = [
            (n, c) for n, c in nicho_counts.items()
            if c < 50
        ]

        if nichos_baixos:

            print("\n⚠️ Nichos com poucas imagens (<50):")

            for nicho, count in nichos_baixos:

                print(f"  - {nicho}: apenas {count}")

        nichos_altos = [
            (n, c) for n, c in nicho_counts.items()
            if c > 300
        ]

        if nichos_altos:

            print("\n✅ Nichos bem preenchidos (>300):")

            for nicho, count in nichos_altos:

                print(f"  - {nicho}: {count}")

    print("\n" + "="*60 + "\n")

    return {
        "total": total_geral,
        "por_nicho": nicho_counts,
        "por_origem": origem_counts,
        "ativas": ativas,
        "inativas": inativas
    }

# =========================
# MAIN
# =========================

if __name__ == "__main__":

    relatorio = gerar_relatorio_completo()
