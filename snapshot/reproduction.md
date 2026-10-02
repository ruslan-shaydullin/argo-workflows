# Reproduce #17024 from this package

This is a deterministic ordering experiment on a disposable local cluster, adapted from [jalvarezz13's report](https://github.com/argoproj/argo-workflows/issues/17024). It is not a production incidence or performance test. The script creates a new namespace, runs an actual executor workload, stops only its controller, ages the completed Pod, requests deletion, and resumes cleanup before Workflow reconciliation. It never edits Workflow status or Pod finalizers.

## Prepare source and images

Use Go 1.26.5 (the checkout's toolchain), Python 3, kubectl, kind and Docker. The recorded host uses Linux arm64 containers; set `DEMO_GOARCH=amd64` for an amd64 kind node; the commands below default to arm64. The supplied patch includes generated schema and all new files. In a new checkout:

```sh
git clone https://github.com/argoproj/argo-workflows.git argo-17024
cd argo-17024
export GOTOOLCHAIN=go1.26.5
export DEMO_GOARCH=arm64 # use amd64 for an amd64 kind node
export GOFLAGS='-mod=readonly -tags=kubernetes_protomessage_one_more_release'
git checkout dadd69141c570fa678f7d51ee6decfe3fa77f109
# BUNDLE is the absolute path of the unpacked local submission bundle.
export BUNDLE=/path/to/unpacked-bundle
git apply --check "$BUNDLE/argo-17024.patch"
mkdir -p .test/17024-baseline .test/17024-candidate
GOTOOLCHAIN=go1.26.5 CGO_ENABLED=0 GOOS=linux GOARCH="$DEMO_GOARCH" go build -buildvcs=false -o .test/17024-baseline/workflow-controller ./cmd/workflow-controller
cp "$BUNDLE/Dockerfile.controller" .test/17024-baseline/Dockerfile
docker build -t argo-17024:baseline .test/17024-baseline
git apply "$BUNDLE/argo-17024.patch"
GOTOOLCHAIN=go1.26.5 CGO_ENABLED=0 GOOS=linux GOARCH="$DEMO_GOARCH" go build -buildvcs=false -o .test/17024-candidate/workflow-controller ./cmd/workflow-controller
cp "$BUNDLE/Dockerfile.controller" .test/17024-candidate/Dockerfile
docker build -t argo-17024:candidate .test/17024-candidate
```

Do not apply the patch twice or run this against an existing production checkout. This experiment uses the candidate full CRD for both images so the schema is not the variable. Old-schema pruning and old mutating writers are separate upgrade controls, described in [validation.md](validation.md).

```sh
export KUBECONFIG="$PWD/.test/17024-kubeconfig"
kind create cluster --name argo-17024-repro --kubeconfig "$KUBECONFIG" --image kindest/node:v1.35.0
kind load docker-image --name argo-17024-repro argo-17024:baseline argo-17024:candidate
kubectl apply -f manifests/base/crds/full/
kubectl wait --for=condition=Established --timeout=120s crd/workflows.argoproj.io crd/workflowtaskresults.argoproj.io
kubectl get nodes
```

## Run the two outcomes

Allow about 5–7 minutes per run. Each output directory and namespace must be new. The controller image must already be present in the node. Executor is pinned by digest to the reporter's released v4.1.3 image; BusyBox is the sole workload, with no artifacts, memoization or user callbacks.

```sh
python3 "$BUNDLE/reproduce.py" --source "$PWD" --kubeconfig "$KUBECONFIG" \
  --namespace argo-17024-repro-base --image argo-17024:baseline \
  --expect baseline-loss --output .test/17024-baseline-result
python3 "$BUNDLE/reproduce.py" --source "$PWD" --kubeconfig "$KUBECONFIG" \
  --namespace argo-17024-repro-final --image argo-17024:candidate \
  --expect candidate-capture --output .test/17024-candidate-result
```

Expected baseline: cleanup removes the aged Pod while the persisted node is still Running; after normal workers resume the node becomes `Error: pod deleted`. Expected candidate: the same Pod UID and barrier remain during the 40-second delayed-reconciliation observation; after normal reconciliation resumes, the recorded node is Succeeded with `taskResultSynced=true` and the original `capturedPodUID`, and the Pod becomes absent. The sampled observations do not resolve the interval between result publication and cleanup; ordering is established by the protocol and separate checks. A failed assertion or timeout is a failed/inconclusive run, not a pass. The script records objects and commands locally and scales its controller to zero on exit; it leaves the namespace and output for inspection. Keep the output private until reviewed. After saving evidence, delete only this disposable cluster:

```sh
kind delete cluster --name argo-17024-repro
```

## In-tree regression commands

The final `costs.md` provides the measured call-count and hydration test/benchmark commands, fixture parameters, exact units and noise limits. The independent standard-library helper suite runs without Kubernetes, SQL, download or evidence-directory access:

```sh
make test-status-capture
```

`make pre-commit -B` is the project-required integration check. Run controller tests on Linux for the full package: native macOS omits Linux process/cgroup behavior and cannot establish the unfiltered Linux suite result. Runtime reader/error/retry observations and the distinction between new runs and unchanged historical boundaries are recorded in [validation.md](validation.md). The supplementary raw evidence records source hashes and explicit setup failures; it is not an installer and has no credentials.
