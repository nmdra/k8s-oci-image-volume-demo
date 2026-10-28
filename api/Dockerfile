FROM python:3.11-slim

# CPU-only ONNX Runtime via FastEmbed (no PyTorch, no bundled weights).
RUN pip install --no-cache-dir fastembed==0.9.1

WORKDIR /app
COPY server.py /app/server.py

# Ensures a missing volume cannot trigger a runtime Hugging Face download.
ENV HF_HUB_OFFLINE=1
EXPOSE 8000
CMD ["python", "-u", "server.py"]
