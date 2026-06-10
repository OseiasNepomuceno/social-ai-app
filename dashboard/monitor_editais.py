import requests
from datetime import datetime, timedelta
from dashboard.picoclaw_agent import chamar_picoclaw

# Configuração de palavras-chave para o filtro inicial (braçal/rápido)
PALAVRAS_CHAVE = ["tecnologia", "inteligência artificial", "software", "dados", "consultoria", "contabilidade"]

def buscar_editais_recentes_pncp(dias_atras=1):
    """
    Step 1: O Olheiro - Consome a API pública do PNCP buscando compras/editais
    publicados nos últimos dias.
    """
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=dias_atras)
    
    # Formato de data exigido pela API do PNCP: AAAAMMDD
    str_inicio = data_inicio.strftime("%Y%m%d")
    str_fim = data_fim.strftime("%Y%m%d")
    
    # URL da API pública do PNCP para consulta de contratações por período
    url = "https://pncp.gov.br/api/consulta/v1/contratacoes"
    params = {
        "dataInicial": str_inicio,
        "dataFinal": str_fim,
        "pagina": 1,
        "tamanhoPagina": 50 # Puxa os 50 mais recentes do dia
    }
    
    try:
        print(f"🔄 Buscando editais no PNCP de {data_inicio.strftime('%d/%m')} até hoje...")
        print(f"URL: {url}")
        print(f"PARAMS: {params}")
        
        response = requests.get(
            url,
            params=params,
            timeout=15
        )
        
        print(f"STATUS: {response.status_code}")
        print(f"RESPOSTA: {response.text[:1000]}")

        if response.status_code != 200:
            print(f"⚠️ Erro ao acessar API do PNCP: Status {response.status_code}")
            return []
            
        dados = response.json()
        editais_brutos = dados.get("data", [])
        print(f"📋 {len(editais_brutos)} editais brutos encontrados no período.")
        
        # Filtro inicial por palavra-chave para economizar tokens do DeepSeek
        editais_filtrados = []
        for edital in editais_brutos:
            objeto = edital.get("objetoCompra", "").lower()
            if any(palavra in objeto for palabra in PALAVRAS_CHAVE):
                editais_filtrados.append({
                    "id": edital.get("id"),
                    "orgao": edital.get("orgaoEntidade", {}).get("razaoSocial"),
                    "objeto": edital.get("objetoCompra"),
                    "valor_estimado": edital.get("valorTotalEstimado"),
                    "link": f"https://pncp.gov.br/app/editais/{edital.get('orgaoEntidade', {}).get('cnpj')}/{edital.get('anoCompra')}/{edital.get('numeroCompra')}"
                })
                
        print(f"🎯 {len(editais_filtrados)} editais passaram pelo pré-filtro de interesse.")
        return editais_filtrados
        
    except Exception as e:
        print(f"❌ Erro na execução do Olheiro PNCP: {e}")
        return []

def analisar_edital_com_deepseek(edital, nicho_cliente="Tecnologia e Automação"):
    """
    Step 2 e 3: A Filtragem Cognitiva e Decisão.
    O PicoClaw passa o edital pré-filtrado para o DeepSeek decidir se vale a pena.
    """
    prompt = f"""
    Você é o analista de licitações inteligente da plataforma CoreGov.
    Sua missão é avaliar se o edital abaixo é uma oportunidade real para um cliente do nicho: '{nicho_cliente}'.

    Dados do Edital:
    - Órgão: {edital['orgao']}
    - Objeto do Contrato: {edital['objeto']}
    - Valor Estimado: R$ {edital['valor_estimado']}

    Avalie criteriosamente. Se o edital for apenas compra de hardware comum (computadores, mouses) ou suporte básico que não envolva {nicho_cliente}, classifique como REJEITADO.
    Se envolver desenvolvimento, automação, IA, ciência de dados ou consultoria estratégica, classifique como RECOMENDADO.

    Responda EXATAMENTE neste formato estruturado:
    DECISÃO: [RECOMENDADO ou REJEITADO]
    MOTIVO: (Explique em uma frase curta por que tomou essa decisão)
    RESUMO: (3 pontos críticos do que o órgão está pedindo)
    """
    
    # Chama o motor do DeepSeek através do seu orquestrador PicoClaw
    resultado = chamar_picoclaw(prompt, timeout=30)
    
    if resultado.get("success"):
        conteudo = resultado["conteudo"]
        # Parse simples da resposta estruturada
        linhas = conteudo.split("\n")
        analise = {"link": edital["link"], "orgao": edital["orgao"], "valor": edital["valor_estimado"]}
        
        for linha in linhas:
            if "DECISÃO:" in linha:
                analise["decisao"] = linha.split("DECISÃO:")[1].strip()
            elif "MOTIVO:" in linha:
                analise["motivo"] = linha.split("MOTIVO:")[1].strip()
            elif "RESUMO:" in linha:
                analise["resumo"] = conteudo.split("RESUMO:")[1].strip()
                break
        return analise
    else:
        print(f"❌ Falha na análise cognitiva do edital {edital['id']}")
        return None
