import os
import io
import time  # Controla o fluxo de requisições e evita o Errno 11
import uuid  # Gera hashes únicos e mitiga erro 409 Duplicate
import requests
from PIL import Image, ImageEnhance
from supabase import create_client 

# Configurações de ambiente puxadas automaticamente
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Inicialização padrão do SDK (usado apenas para ler/atualizar dados da tabela)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_variacao_para_supabase(buffer_imagem, nome_arquivo_variacao):
    """
    🚀 PLANO B ATIVADO: Envia o arquivo diretamente via API REST do Supabase.
    Ignora completamente bugs de versão de biblioteca e contorna o bloqueio de RLS
    passando os cabeçalhos administrativos diretos.
    """
    try:
        bucket_name = "social-ai"
        url = f"{SUPABASE_URL}/storage/v1/object/{bucket_name}/variacoes/{nome_arquivo_variacao}"
        
        # Cabeçalhos brutos usando a Service Role Key como master key
        headers = {
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "ApiKey": SUPABASE_KEY,
            "Content-Type": "image/jpeg",
            "x-upsert": "true"
        }
        
        # Realiza o POST com os bytes brutos da memória do Render
        response = requests.post(url, headers=headers, data=buffer_imagem.getvalue(), timeout=15)
        
        if response.status_code in [200, 201]:
            # Retorna a URL pública construída
            return f"{SUPABASE_URL}/storage/v1/object/public/{bucket_name}/variacoes/{nome_arquivo_variacao}"
        
        print(f"❌ Erro na API do Storage ({response.status_code}): {response.text}")
        return None
    except Exception as e:
        print(f"❌ Falha no upload direto via REST: {str(e)}")
        return None


def processar_e_salvar_variacoes(imagem_original):
    """
    Baixa uma imagem original cadastrada, faz as modificações visuais
    e cria novos registros vinculados na mesma tabela do Supabase.
    """
    try:
        id_pai = imagem_original["id"]
        url_original = imagem_original["image_url"]  
        nicho = imagem_original.get("nicho", "geral")
        rede = imagem_original.get("rede", "linkedin")
        categoria = imagem_original.get("categoria", "corporativo")
        estilo = imagem_original.get("estilo", "premium")
        formato = imagem_original.get("formato", "quadrado")
        origem = imagem_original.get("origem", "pixabay")
        tags = imagem_original.get("tags", nicho)

        # 1. Baixa a imagem atual direto pela URL pública
        response = requests.get(url_original, timeout=15)
        if response.status_code != 200:
            return 0
            
        img_original = Image.open(io.BytesIO(response.content))
        
        # Gera um hash curto exclusivo para esta execução evitar colisões antigas
        hash_unico = uuid.uuid4().hex[:8]
        nome_base = f"var_origem_{id_pai}_{hash_unico}"
        
        # Definimos 2 variações excelentes que mudam a assinatura digital do arquivo
        variacoes_config = [
            {"tipo": "variacao_flip", "acao": lambda img: img.transpose(Image.FLIP_LEFT_RIGHT)},
            {"tipo": "variacao_filtro", "acao": lambda img: ImageEnhance.Contrast(img).enhance(1.20)}
        ]
        
        contador_sucesso = 0
        
        for i, var in enumerate(variacoes_config, 1):
            img_nova = var["acao"](img_original)
            
            buffer = io.BytesIO()
            img_nova.convert('RGB').save(buffer, format="JPEG", quality=85)
            buffer.seek(0)
            
            nome_arquivo_novo = f"{nome_base}_v{i}_{var['tipo']}.jpg"
            
            # Envia usando a nova função via requisição HTTP direta
            url_publica_nova = upload_variacao_para_supabase(buffer, nome_arquivo_novo)
            buffer.close()
            
            if url_publica_nova:
                payload = {
                    "rede": rede,
                    "nicho": nicho,
                    "categoria": categoria,
                    "estilo": estilo,
                    "formato": formato,
                    "origem": origem,
                    "tags": tags,
                    "image_url": url_publica_nova,
                    "tipo_midia": var["tipo"],       
                    "id_imagem_pai": id_pai,
                    "processado_agente": True
                }
                supabase.table("media_library").insert(payload).execute()
                contador_sucesso += 1
                
                # Cadência interna controlada
                time.sleep(0.8)
                
        return contador_sucesso

    except Exception as e:
        print(f"❌ Falha ao multiplicar imagem ID {imagem_original.get('id')}: {str(e)}")
        return 0


def iniciar_multiplicacao_banco_existente(limite_por_rodada=20):
    """
    Função principal. Busca imagens originais não processadas pelo agente
    para criar variações e evitar loops e redundâncias.
    """
    print("\n" + "="*60)
    print("🚀 INICIANDO AGENTE MULTIPLICADOR DE IMAGENS DISPONÍVEIS")
    print("="*60)
    
    try:
        resposta_banco = supabase.table("media_library")\
            .select("*")\
            .is_("id_imagem_pai", "null")\
            .eq("processado_agente", False)\
            .limit(limite_por_rodada)\
            .execute()
            
        imagens_originais = resposta_banco.data
        
        if not imagens_originais:
            print("✨ Nenhuma imagem original pendente de variação encontrada no banco.")
            return

        total_encontrado = len(imagens_originais)
        print(f"📦 Lote selecionado: Processando {total_encontrado} imagens inéditas da media_library.")
        
        total_novas_criadas = 0
        for idx, img in enumerate(imagens_originais, 1):
            id_pai = img["id"]
            
            geradas = processar_e_salvar_variacoes(img)
            total_novas_criadas += geradas
            
            # Marca o pai como processado
            supabase.table("media_library")\
                .update({"processado_agente": True})\
                .eq("id", id_pai)\
                .execute()
            
            # Cadência externa controlada
            time.sleep(0.5)
            
            if idx % 10 == 0 or idx == total_encontrado:
                print(f"⚙️ Progresso: [{idx}/{total_encontrado}] imagens originais processadas...")

        print("\n" + "="*60)
        print(f"✅ CONCLUÍDO: O agente adicionou +{total_novas_criadas} variações exclusivas ao banco de produção!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"❌ Erro crítico no pipeline de multiplicação: {str(e)}")
