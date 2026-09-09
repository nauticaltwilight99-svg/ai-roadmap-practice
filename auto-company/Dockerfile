FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GEMINI_PROJECT_DIR=/workspace/project \
    GEMINI_AGENT_WIN=/app/scripts/core/gemini-agent.py \
    GEMINI_PYTHON_BIN=/usr/local/bin/python

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY dashboard ./dashboard
COPY scripts/core ./scripts/core
COPY config ./config
RUN mkdir -p /workspace/project/.runtime /workspace/project/outbox

EXPOSE 8787

CMD ["python", "dashboard/server.py", "--host", "0.0.0.0", "--port", "8787"]