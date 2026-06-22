Write-Output "=== Verificando SHA dos arquivos ==="

$pyResult = gh api repos/OseiasNepomuceno/social-ai-app/contents/dashboard/picoclawsite.py --jq '.sha' 2>&1
Write-Output "picoclawsite.py SHA: $pyResult"

$htmlResult = gh api repos/OseiasNepomuceno/social-ai-app/contents/dashboard/templates/base.html --jq '.sha' 2>&1
Write-Output "base.html SHA: $htmlResult"

Write-Output "=== Verificando se DeepSeek foi removido do picoclawsite.py ==="
$pyContent = gh api repos/OseiasNepomuceno/social-ai-app/contents/dashboard/picoclawsite.py --jq '.content' 2>&1
if ($LASTEXITCODE -eq 0) {
    $decoded = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($pyContent))
    if ($decoded -match "MonitorRequest|monitor-editais|monitorar-editais") {
        Write-Output "ERRO: Ainda contém código DeepSeek!"
    } else {
        Write-Output "OK: DeepSeek removido do picoclawsite.py"
    }
} else {
    Write-Output "Erro ao buscar picoclawsite.py: $pyContent"
}

Write-Output "=== Verificando se Monitor PNCP foi removido do base.html ==="
$htmlContent = gh api repos/OseiasNepomuceno/social-ai-app/contents/dashboard/templates/base.html --jq '.content' 2>&1
if ($LASTEXITCODE -eq 0) {
    $decoded = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($htmlContent))
    if ($decoded -match "Monitor Oportunidades PNCP|monitor-editais") {
        Write-Output "ERRO: Ainda contém link Monitor PNCP!"
    } else {
        Write-Output "OK: Monitor PNCP removido do base.html"
    }
} else {
    Write-Output "Erro ao buscar base.html: $htmlContent"
}
