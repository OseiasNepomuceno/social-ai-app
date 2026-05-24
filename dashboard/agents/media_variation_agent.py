import os
import io
import requests
from PIL import Image, ImageEnhance
from supabase import create_client

# Configurações de ambiente puxadas automaticamente
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_variacao_para_supabase(buffer_imagem, nome_arquivo_variacao):
    """Envia a variação processada na memória direto para o Storage do Supabase"""
    try:
        bucket_name = "media_library_bucket" 
        
        # Faz o upload direto dos bytes sem salvar nada no Render
        supabase.storage.from_(bucket_name).upload(
            path=f"variacoes/{nome_arquivo_variacao}",
            file=buffer_imagem.getvalue(),
            file_options={"content-type": "image/jpeg"}
        )
        
        # Gera o link público permanente para ser usado na postagem
        public_url = supabase.storage.from_(bucket_name).get_public_url(f"variacoes/{nome_arquivo_variacao}")
        return public_url
    except Exception as e:
        print(f"❌ Erro ao enviar arquivo para o Storage: {str(e)}")
        return None


def processar_e_salvar_variacoes(imagem_original):
    """
    Baixa uma imagem original cadastrada, faz as modificações visuais
    e cria novos registros vinculados na mesma tabela do Supabase.
    """
    try:
        id_pai = imagem_original["id"]
        url_original = imagem_original["image_url"]  
        nicho = imagem_original["nicho"]
        rede = imagem_original["rede"]
        categoria = imagem_original.get("categoria", "corporativo")
        estilo = imagem_original.get("estilo", "premium")
        formato = imagem_original.get("formato", "quadrado")
        tema_original = imagem_original.get("tema", "Variação de Imagem Própria")

        # 1. Baixa a imagem atual direto pela URL pública
        response = requests.get(url_original, timeout=15)
        if response.status_code != 200:
            return 0
            
        img_original = Image.open(io.BytesIO(response.content))
        nome_base = f"var_origem_{id_pai}"
        
        # Definimos 2 variações excelentes que mudam a assinatura digital do arquivo
        variacoes_config = [
            {"tipo": "variacao_flip", "acao": lambda img: img.transpose(Image.FLIP_LEFT_RIGHT)},
            {"tipo": "variacao_filtro", "acao": lambda img: ImageEnhance.Contrast(img).enhance(1.20)}
        ]
        
        contador_sucesso = 0
        
        for i, var in enumerate(variacoes_config, 1):
            # Executa a transformação na imagem
            img_nova = var["acao"](img_original)
            
            # Comprime o arquivo em memória como JPEG otimizado
            buffer = io.BytesIO()
            img_nova.convert('RGB').save(buffer, format="JPEG", quality=85)
            buffer.seek(0)
            
            # Nome único do arquivo transformado
            nome_arquivo_novo = f"{nome_base}_v{i}_{var['tipo']}.jpg"
            
            # Envia para a nuvem
            url_publica_nova = upload_variacao_para_supabase(buffer, nome_arquivo_novo)
            
            if url_publica_nova:
                # Insere o novo registro clonando as propriedades estruturais exatas
                payload = {
                    "tema": tema_original,
                    "rede": rede,
                    "nicho": nicho,
                    "categoria": categoria,
                    "estilo": estilo,
                    "formato": formato,
                    "image_url": url_publica_nova,
                    "tipo_midia": var["tipo"],       
                    "id_imagem_pai": id_pai          
                }
                supabase.table("media_library").insert(payload).execute()
                contador_sucesso += 1
                
        return contador_sucesso

    except Exception as e:
        print(f"❌ Falha ao multiplicar imagem ID {imagem_original.get('id')}: {str(e)}")
        return 0


def iniciar_multiplicacao_banco_existente(limite_por_rodada=50):
    """
    Função principal. Busca imagens originais não processadas pelo agente
    para criar variações e evitar loops e redundâncias.
    """
    print("\n" + "="*60)
    print("🚀 INICIANDO AGENTE MULTIPLICADOR DE IMAGENS DISPONÍVEIS")
    print("="*60)
    
    try:
        # Puxa imagens originais que ainda NÃO foram processadas pelo agente
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
            
            # Processa e salva as variações no banco e storage
            geradas = processar_e_salvar_variacoes(img)
            total_novas_criadas += geradas
            
            # MARCA A IMAGEM COMO PROCESSADA para ela nunca mais voltar na query do limit()
            supabase.table("media_library")\
                .update({"processado_agente": True})\
                .eq("id", id_pai)\
                .execute()
            
            if idx % 10 == 0 or idx == total_encontrado:
                print(f"⚙️ Progresso: [{idx}/{total_encontrado}] imagens originais processadas com sucesso...")

        print("\n" + "="*60)
        print(f"✅ CONCLUÍDO: O agente adicionou +{total_novas_criadas} variações exclusivas ao banco de produção!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"❌ Erro crítico no pipeline de multiplicação: {str(e)}")
