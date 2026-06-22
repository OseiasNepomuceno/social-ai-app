# Script to update picoclawsite.py and base.html on GitHub
# Removes DeepSeek / Monitor Oportunidades PNCP

$repo = "OseiasNepomuceno/social-ai-app"
$branch = "main"
$commitMessage = "remove deepseek / monitor oportunidades pncp"
$workDir = "C:\Users\oseia\.picoclaw\workspace\social-ai-app"

function Get-Base64 {
    param([string]$text)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($text)
    return [Convert]::ToBase64String($bytes)
}

Write-Output "=== Step 1: Updating picoclawsite.py ==="

$pyContent = Get-Content -Path "$workDir\picoclawsite_updated.py" -Raw -Encoding UTF8
$pyBase64 = Get-Base64 $pyContent
$pySha = "68f5b30a154c0d3eef1957d6db16a44f734074ff"

$jsonPayload = @{
    message = $commitMessage
    branch  = $branch
    content = $pyBase64
    sha     = $pySha
} | ConvertTo-Json -Compress

[System.IO.File]::WriteAllText("$workDir\py_payload.json", $jsonPayload, [System.Text.UTF8Encoding]::new($false))

$pyResult = gh api "repos/$repo/contents/dashboard/picoclawsite.py" --method PUT --input "$workDir\py_payload.json" --jq '.commit.sha' 2>&1
Write-Output "picoclawsite.py commit SHA: $pyResult"

Write-Output "=== Step 2: Updating base.html ==="

$htmlContent = Get-Content -Path "$workDir\base_updated.html" -Raw -Encoding UTF8
$htmlBase64 = Get-Base64 $htmlContent
$htmlSha = "4b8e77159c449eab81abcfcd54bd3dafeda7611f"

$jsonPayload2 = @{
    message = $commitMessage
    branch  = $branch
    content = $htmlBase64
    sha     = $htmlSha
} | ConvertTo-Json -Compress

[System.IO.File]::WriteAllText("$workDir\html_payload.json", $jsonPayload2, [System.Text.UTF8Encoding]::new($false))

$htmlResult = gh api "repos/$repo/contents/dashboard/templates/base.html" --method PUT --input "$workDir\html_payload.json" --jq '.commit.sha' 2>&1
Write-Output "base.html commit SHA: $htmlResult"

Write-Output "=== Done! ==="
