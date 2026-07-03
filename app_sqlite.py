"""
Entry point para o Hugging Face Spaces com SQLite.
Define USE_SQLITE=true antes de importar o app.
"""
import os
import sys

# =========================
# FORÇAR USO DE SQLITE
# =========================
os.environ["USE_SQLITE"] = "true"

# Garantir que /data existe (HF Spaces persistent storage)
os.makedirs("/data/db", exist_ok=True)
os.makedirs("/data/uploads", exist_ok=True)
os.makedirs("/data/storage", exist_ok=True)

# =========================
# IMPORTAR O APP (já usa db_adapter)
# =========================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dashboard.app import app

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    port = int(os.getenv("PORT", 7860))
    print(f"🚀 COREGOV App rodando com SQLite na porta {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
