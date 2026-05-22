FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; port=os.getenv('PORT', '8000'); urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=3).read()" || exit 1

CMD ["sh", "-c", "export API_BASE_URL=\"${API_BASE_URL:-http://127.0.0.1:${PORT:-8000}}\" && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} & streamlit run frontend/app.py --server.address 0.0.0.0 --server.port ${STREAMLIT_PORT:-8501} --server.headless true --browser.gatherUsageStats false"]