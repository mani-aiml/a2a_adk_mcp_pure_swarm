FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agents.yaml .
COPY otel_setup.py .
COPY shared/ shared/
COPY provenance_agent/ provenance_agent/
EXPOSE 8080
CMD ["uvicorn", "provenance_agent.agent:a2a_app", "--host", "0.0.0.0", "--port", "8080"]
