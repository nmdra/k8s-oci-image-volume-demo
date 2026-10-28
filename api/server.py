import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from fastembed import TextEmbedding

MODEL_DIR = Path('/models')
MODEL_FILE = MODEL_DIR / 'model_optimized.onnx'
if not MODEL_FILE.is_file():
    raise RuntimeError(f'Missing mounted model weights: {MODEL_FILE}')

# The ONLY source of model files is the read-only OCI image volume.
# This does not download the model when the application starts.
model = TextEmbedding(
    model_name='BAAI/bge-small-en-v1.5',
    specific_model_path=str(MODEL_DIR),
    threads=2,
)


class Handler(BaseHTTPRequestHandler):
    def respond(self, code, payload):
        data = json.dumps(payload).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/health':
            self.respond(200, {'status': 'ok', 'model_file': str(MODEL_FILE)})
        else:
            self.respond(404, {'error': 'Use GET /health or POST /embed'})

    def do_POST(self):
        if self.path != '/embed':
            self.respond(404, {'error': 'Use POST /embed'})
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size <= 0 or size > 65536:
                raise ValueError('Body must be between 1 and 65536 bytes')
            request = json.loads(self.rfile.read(size))
            text = request.get('text')
            if not isinstance(text, str) or not text.strip():
                raise ValueError('Expected a nonempty string in "text"')
            vector = next(model.embed([text]))
            self.respond(200, {
                'model': 'BAAI/bge-small-en-v1.5',
                'dimensions': len(vector),
                'embedding': vector.tolist(),
            })
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.respond(400, {'error': str(exc)})


if __name__ == '__main__':
    print('Model loaded from the OCI image volume at /models', flush=True)
    HTTPServer(('0.0.0.0', 8000), Handler).serve_forever()
