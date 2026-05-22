import os
import random
from PIL import Image, ImageEnhance, ImageFilter

def criar_variacoes_imagem(caminho_original, pasta_destino, multiplicador=3):
    """
    Pega uma imagem original e gera variações únicas baseadas no multiplicador.
    Salva as novas imagens na pasta de destino.
    """
    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)
        
    try:
        nome_arquivo = os.path.basename(caminho_original)
        nome_base, ext = os.path.splitext(nome_arquivo)
        
        # Garante que extensões sejam compatíveis com o Pillow
        if ext.lower() not in ['.jpg', '.jpeg', '.png', '.webp']:
            return 0

        # Abre a imagem original
        img = Image.open(caminho_original)
        variacoes_geradas = 0

        # --- Variação 1: Espelhamento Horizontal (Flip) ---
        if multiplicador >= 1:
            img_flip = img.transpose(Image.FLIP_LEFT_RIGHT)
            caminho_salvar = os.path.join(pasta_destino, f"{nome_base}_v1_flip{ext}")
            img_flip.save(caminho_salvar, quality=85, optimize=True)
            variacoes_geradas += 1

        # --- Variação 2: Ajuste de Tonalidade/Brilho (Filtro Premium) ---
        if multiplicador >= 2:
            # Melhora o contraste de leve (1.2) e reduz um pouquinho o brilho para dar tom dramático/premium
            enhancer_contrast = ImageEnhance.Contrast(img)
            img_filter = enhancer_contrast.enhance(1.15)
            enhancer_brightness = ImageEnhance.Brightness(img_filter)
            img_filter = enhancer_brightness.enhance(0.95)
            
            caminho_salvar = os.path.join(pasta_destino, f"{nome_base}_v2_filter{ext}")
            img_filter.save(caminho_salvar, quality=85, optimize=True)
            variacoes_geradas += 1

        # --- Variação 3: Crop Inteligente ou Zoom de Foco ---
        if multiplicador >= 3:
            largura, altura = img.size
            # Recorta 5% das bordas para criar um enquadramento ligeiramente diferente (efeito zoom)
            margem_x = int(largura * 0.05)
            margem_y = int(altura * 0.05)
            
            img_cropped = img.crop((margem_x, margem_y, largura - margem_x, altura - margem_y))
            # Redimensiona de volta para o tamanho original para não perder resolução
            img_cropped = img_cropped.resize((largura, altura), Image.Resampling.LANCZOS)
            
            caminho_salvar = os.path.join(pasta_destino, f"{nome_base}_v3_zoom{ext}")
            img_cropped.save(caminho_salvar, quality=85, optimize=True)
            variacoes_geradas += 1

        return variacoes_geradas

    except Exception as e:
        print(f"❌ Erro ao processar variações para {caminho_original}: {str(e)}")
        return 0


def executar_pipeline_variacao(pasta_origem="downloads/originais", pasta_saida="downloads/banco_proprio"):
    """
    Função principal que será chamada pelo seu executor geral.
    Varre a pasta de imagens baixadas e processa a multiplicação.
    """
    print("\n" + "="*50)
    print("🤖 INICIANDO AGENTE DE VARIAÇÃO DE MÍDIA (DATA AUGMENTATION)")
    print("="*50)
    
    if not os.path.exists(pasta_origem):
        print(f"⚠️ Pasta de origem '{pasta_origem}' não encontrada. Nenhum download prévio detectado.")
        return

    arquivos = [os.path.join(pasta_origem, f) for f in os.listdir(pasta_origem) if os.path.isfile(os.path.join(pasta_origem, f))]
    total_imagens = len(arquivos)
    total_novas_imagens = 0

    print(f"📸 Encontradas {total_imagens} imagens originais para processamento.")

    for i, caminho_img in enumerate(arquivos, 1):
        # Chama a função para criar as 3 variações
        geradas = criar_variacoes_imagem(caminho_img, pasta_saida, multiplicador=3)
        total_novas_imagens += geradas
        
        if i % 100 == 0 or i == total_imagens:
            print(f"⚙️ Progresso: [{i}/{total_imagens}] imagens originais processadas...")

    print("\n" + "="*50)
    print(f"✅ SUCESSO: O agente gerou {total_novas_imagens} novas variações!")
    print(f"📂 Seu banco próprio agora conta com {total_imagens + total_novas_imagens} imagens prontas.")
    print("="*50 + "\n")
