# Multi-stage Dockerfile for Google ADK Multi-Agent Analyst
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app

COPY --from=builder /root/.local /opt/python
ENV PATH=/opt/python/bin:$PATH
ENV PYTHONPATH=/opt/python/lib/python3.11/site-packages
ENV PYTHONUNBUFFERED=1

COPY src/ src/
COPY api/ api/
COPY data/ data/
COPY streamlit_app/ streamlit_app/
RUN python data/create_db.py
RUN groupadd --system app && useradd --system --gid app --home-dir /app app \
    && chown -R app:app /app
USER app

EXPOSE 8000 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
