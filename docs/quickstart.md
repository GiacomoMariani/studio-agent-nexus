# Quick start

```bash
# 1. Install
python -m venv .venv && source .venv/bin/activate   # PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt

# 2. Configure
cp .env.example .env        # PowerShell: Copy-Item .env.example .env
# set at least: APP_API_KEY=dev-secret-key  and  API_BASE_URL=http://localhost:8000

# 3. Run the backend
uvicorn main:app --reload   # http://127.0.0.1:8000  · docs at /docs  · health at /health

# 4. Run the UI (second terminal)
streamlit run frontend/app.py   # http://localhost:8501
```

Or run both together in one container:

```bash
docker build -t studio-agent-nexus .
docker run -p 8000:8000 -p 8501:8501 --env-file .env studio-agent-nexus
```
