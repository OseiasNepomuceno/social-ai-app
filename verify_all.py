# verify_all.py
import os

with open('dashboard/app.py', 'rb') as f:
    c = f.read()

checks = [
    (b'from dashboard.analisador_estatuto import', 'Import do analisador_estatuto'),
    (b'@app.route("/analisar-estatuto")', 'Rota GET /analisar-estatuto'),
    (b'@app.route("/api/analisar-estatuto"', 'Rota POST /api/analisar-estatuto'),
    (b'api_analisar_estatuto', 'Funcao api_analisar_estatuto'),
    (b'gerar_pdf_diagnostico', 'Chamada gerar_pdf_diagnostico'),
    (b'analisar_estatuto_picoclaw', 'Chamada analisar_estatuto_picoclaw'),
]

print("=== VERIFICACAO DO ANALISADOR DE ESTATUTO ===\n")
all_ok = True
for pattern, msg in checks:
    ok = pattern in c
    status = "OK" if ok else "FALHA"
    if not ok:
        all_ok = False
    print(f"  [{status}] {msg}")

# Verificar template
template_path = 'dashboard/templates/analisar_estatuto.html'
if os.path.exists(template_path):
    print(f"  [OK] Template analisar_estatuto.html existe ({os.path.getsize(template_path)} bytes)")
else:
    print(f"  [FALHA] Template analisar_estatuto.html nao encontrado!")
    all_ok = False

# Verificar modulo
modulo_path = 'dashboard/analisador_estatuto.py'
if os.path.exists(modulo_path):
    print(f"  [OK] Modulo analisador_estatuto.py existe ({os.path.getsize(modulo_path)} bytes)")
else:
    print(f"  [FALHA] Modulo analisador_estatuto.py nao encontrado!")
    all_ok = False

print()
if all_ok:
    print("✅ TUDO OK! O servico de analise de estatuto esta pronto para uso.")
    print("   Acesse: https://app.coregov.com.br/analisar-estatuto")
else:
    print("❌ Ha problemas a resolver.")
