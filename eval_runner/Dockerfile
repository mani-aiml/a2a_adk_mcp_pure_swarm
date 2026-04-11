FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# Eval runner needs `adk eval` (google-adk[eval]); agent images stay on [a2a] only.
RUN pip install --no-cache-dir -r requirements.txt pytest pyyaml \
    && pip install --no-cache-dir 'google-adk[eval]'

COPY . .

ENV PYTHONPATH=/app

RUN chmod +x evaluation/docker/run_network_eval.sh evaluation/run_evals.sh

ENTRYPOINT ["./evaluation/docker/run_network_eval.sh"]
CMD []
