# kind + Kubernetes OCI Image Volume + real embedding model

Demonstrates KEP-4639 using two independently built OCI images:

- `demo/embed-api:v1`: Python + FastEmbed web server; **no model files inside**
- `demo/embed-weights:v1`: ONNX model weights + tokenizer; **no runnable server**

The model is `BAAI/bge-small-en-v1.5` (~67 MB, 384-dimensional vectors). The model image is mounted read-only at `/models` by `spec.volumes[].image` and the usual `volumeMounts` entry. Requires Docker, kind, kubectl, and internet during the *model image build*.

## 1. Cluster

Use an existing kind cluster with Kubernetes 1.36+ and compatible containerd (2.1+), OR create a separate up-to-date test cluster. Ensure your kind CLI supports the Kubernetes version. Example:

```bash
kind create cluster --name oci-embed --image kindest/node:v1.36.1@sha256:3489c7674813ba5d8b1a9977baea8a6e553784dab7b84759d1014dbd78f7ebd5
kubectl --context kind-oci-embed get nodes -o wide
```

For an existing cluster, replace `oci-embed` in the following commands with the name from `kind get clusters` and use the corresponding kubectl context. Check versions:

```bash
kubectl version
kind version
# For the newly created cluster:
docker exec oci-embed-control-plane containerd --version
```

## 2. Build both images

Run from the root of this project:

```bash
docker build -t demo/embed-api:v1 ./api
docker build -t demo/embed-weights:v1 ./weights
```

The second image build downloads the model once from Hugging Face and creates a `FROM scratch` data-only image with `model_optimized.onnx`, tokenizer metadata, and other required files at its root.

## 3. Import images into kind

```bash
kind load docker-image demo/embed-api:v1 demo/embed-weights:v1 --name oci-embed
```

`imagePullPolicy: Never` and `pullPolicy: Never` make kubelet use exactly those node-local imported images, so no registry push/pull is needed. On a multinode kind cluster, `kind load` imports into all its nodes.

## 4. Deploy

```bash
kubectl --context kind-oci-embed apply -f k8s/deployment.yaml
kubectl --context kind-oci-embed rollout status deployment/embedding-api --timeout=180s
kubectl --context kind-oci-embed get pods -o wide
kubectl --context kind-oci-embed logs deployment/embedding-api
```

Check that ONNX files are mounted in the running API container:

```bash
kubectl --context kind-oci-embed exec deployment/embedding-api -- ls -lh /models/
```

## 5. Send an embedding request

Run this in one terminal:

```bash
kubectl --context kind-oci-embed port-forward deployment/embedding-api 8000:8000
```

In a second terminal:

```bash
curl -s http://localhost:8000/health
curl -s -X POST http://localhost:8000/embed \
  -H 'Content-Type: application/json' \
  -d '{"text":"Kubernetes can mount OCI model weights"}'
```

If `jq` is installed, inspect just the dimension and first eight numbers:

```bash
curl -s -X POST http://localhost:8000/embed \
  -H 'Content-Type: application/json' \
  -d '{"text":"Kubernetes can mount OCI model weights"}' \
  | jq '{dimensions, first_8: .embedding[:8]}'
```

## 6. Demonstrate reuse

```bash
kubectl --context kind-oci-embed scale deployment/embedding-api --replicas=3
kubectl --context kind-oci-embed rollout status deployment/embedding-api --timeout=180s
kubectl --context kind-oci-embed get pods -o wide
```

All 3 Pods mount `demo/embed-weights:v1`. The model image layers can be shared in the per-node image store. Each server still allocates its own runtime model memory. A single-node kind cluster reuses its local image cache.

## Troubleshooting

```bash
kubectl --context kind-oci-embed describe pods -l app=embedding-api
kubectl --context kind-oci-embed logs deployment/embedding-api
```

- `unknown field "image"`: API server is too old or feature gate disabled. Use Kubernetes 1.36+ for easiest setup.
- `FailedMount` / unsupported image volume: verify containerd 2.1+ and `ImageVolume` support in the kind node image.
- `ErrImageNeverPull` / missing image: `kind load docker-image ... --name oci-embed` again; check the matching cluster name, image names, and tags.
- Model image Docker build fails: check access to `https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q`.
- Docker Desktop ARM64 / amd64: use the same target platform as the kind node images.
- If `kind load` fails with a content digest error when Docker's containerd image store is enabled, see https://kind.sigs.k8s.io/docs/user/known-issues/ and load a single-platform image archive instead.

## Cleanup

```bash
kubectl --context kind-oci-embed delete -f k8s/deployment.yaml
# Only if you created the demo cluster:
kind delete cluster --name oci-embed
```

## References

- https://kubernetes.io/docs/concepts/storage/volumes/#image
- https://kind.sigs.k8s.io/docs/user/quick-start/#loading-an-image-into-your-cluster
- https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q
- https://qdrant.github.io/fastembed/examples/Supported_Models/
