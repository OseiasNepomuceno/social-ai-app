picoclaw_onboard: mkdir -p /opt/render/.picoclaw && /opt/render/project/src/tools/picoclaw onboard
picoclaw_gateway: /opt/render/project/src/tools/picoclaw gateway
dashboard: gunicorn dashboard.app:app
fastapi: uvicorn picoclawsite:app --host 0.0.0.0 --port 10000
release: python3 setup_picoclaw.py
web: python3 setup_picoclaw.py && honcho start

