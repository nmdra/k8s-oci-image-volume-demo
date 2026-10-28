# Build an OCI image that ONLY contains read-only model data.
FROM python:3.11-slim AS download
RUN pip install --no-cache-dir 'huggingface_hub==0.35.3'
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Qdrant/bge-small-en-v1.5-onnx-Q', local_dir='/export', allow_patterns=['*.json', '*.onnx', 'vocab.txt'])" \
    && rm -rf /export/.cache

FROM scratch
COPY --from=download /export/ /
