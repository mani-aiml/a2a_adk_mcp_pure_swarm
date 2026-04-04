FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agents.yaml .
COPY shared/ shared/
COPY orchestrator/ orchestrator/
COPY display.py .
COPY main.py .
COPY otel_setup.py .
CMD ["python", "main.py"]
