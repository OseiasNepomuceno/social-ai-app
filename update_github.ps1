# Get SHA of picoclawsite.py
$shaPy = (gh api repos/OseiasNepomuceno/social-ai-app/contents/dashboard/picoclawsite.py --jq .sha 2>&1)
Write-Output "SHA picoclawsite.py: $shaPy"

# Get SHA of base.html
$shaHtml = (gh api repos/OseiasNepomuceno/social-ai-app/contents/dashboard/templates/base.html --jq .sha 2>&1)
Write-Output "SHA base.html: $shaHtml"
