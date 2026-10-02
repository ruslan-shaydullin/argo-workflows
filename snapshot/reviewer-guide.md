# Review guide: preserve Pod results before cleanup

## 30 seconds: the behavior under review

A Pod can succeed while its persisted Workflow node still says Running. With status capture enabled, the independent cleanup queue can remove an aged terminal Pod's finalizer before Workflow reconciliation records its result. The next reconciliation can report `Error: pod deleted`.

The proposed change retains the finalizer for normal terminal-result cleanup until persisted Workflow state identifies the same Pod UID and has the required result and task synchronization. Cleanup work is reconstructed after controller restart.

```text
Same successful Pod; Workflow reconciliation delayed; deletion requested.

Upstream:  Pod Succeeded → finalizer removed → Pod gone → Workflow Error
Proposed:  Pod Succeeded → finalizer retained → result persisted → cleanup
                                                        └─ Workflow Succeeded
```

Start with the [bundle overview](README.md), [demonstration](demo.mp4), or [text reproduction](reproduction.md). The controlled reproduction establishes this failure ordering; it does not measure production frequency. Its zero-Workflow-worker interval deliberately delays reconciliation.

## Five minutes: why these parts belong together

1. **Record the observed identity with the result.** The optional `status.nodes[*].capturedPodUID` records which Pod incarnation produced the controller-selected node state. For offloaded nodes, saving a row alone is insufficient: the persisted Workflow must publish the reference to that row.
2. **Read before authorizing cleanup.** The worker reads the current owner and its selected node representation, checks the result, synchronization and identity, and protects the Pod mutation with UID/resourceVersion checks. An unavailable storage row is not evidence that the owner is absent.
3. **Recover the obligation after a crash.** Pod informer Add events reconstruct UID-bound cleanup hints; Workflow completion/deletion triggers a scoped sweep. Read/write failures retain retries without needing a new Pod event. Hints do not authorize later mutations: the mutation worker checks current state again.

Recording identity alone would leave independent cleanup unguarded. Guarding cleanup without reconstructing work could leave a Pod held after a crash. These paths implement one behavior and need review together.

The guarantee concerns normal terminal-result cleanup. Verified deleting, absent or replaced owners have their own cleanup disposition; that disposition does not assert result capture. Persisted automatic-restart retirement, nonterminal cancellation, daemon/stop handling and agent cleanup also have distinct paths. Review these explicitly rather than assuming every removal is authorized by `capturedPodUID`.

### Tradeoffs to decide explicitly

| Area | Proposed behavior and limitation |
|---|---|
| Disabled flag | The finalizer remains opt-in. UID recording and common cleanup reads also occur with the flag off. An active raw Pod hint costs one Pod GET and one Workflow GET; encoded nodes add one full hydration. |
| Retained legacy backlog | Whole-map hydration remains per retained encoded Pod. The measured stable cycle for 16 unsupported legacy Pods is 16 Pod GETs, 16 Workflow GETs and 16 full hydrations. These are logical operation counts, not production latency or SQL-query counts. |
| Completed legacy results | Automatic recapture supports only a provable, unchanged single-root ordinary-container success. Even a successful two-step completed Workflow is outside that verifier. It remains held with diagnostics and an explicit evidence-preserving operator procedure. This is a support boundary, not proof that broader recovery is impossible. |
| Upgrade and rollback | Preserving outstanding capture obligations needs a preserving CRD and exclusion of old active controllers and writers. Older typed writers may drop the field on rewrite. Rollback requires resolving those obligations and retaining the newer schema. This controlled transition is not a blanket stop/drain rule for every flag-off installation. |
| Validation | The focused reproduction demonstrates one ordering. The broader test and runtime results are in [validation](validation.md); production latency, full repository-wide tests and remote CI must not be inferred from the demo. |

See [costs and measurement limits](costs.md) before deciding whether the extra reads are acceptable.

## Deep review: follow the protocol through the diff

All paths below are repository-relative and refer to the proposed source, based on `dadd69141c570fa678f7d51ee6decfe3fa77f109`. The patch SHA-256 is `aeba17d588a6fb9434f4d66eeaa72bdc20313a895e6a7eb3476dd2f9c6d11614`.

| Order | Files and entry points | Review question |
|---|---|---|
| 1. Result identity | `pkg/apis/workflow/v1alpha1/workflow_types.go`: `NodeStatus.CapturedPodUID`; `workflow/controller/operator.go`: `assessNodeStatus`, `podCaptureUID` | Is the UID attached to the controller-selected result for the correct owner/node/Pod, including failed results? |
| 2. Publication | `workflow/controller/operator.go`: `persistUpdates`, `reapplyUpdate`, `queuePendingPodRetirements`; `workflow/controller/pod_cleanup.go`: `lookupWorkflowForPodCleanup`, `hydrateWorkflowForPodCleanup`, `queuePodsForCleanup` | Do persistence failures and concurrent identity changes prevent premature cleanup? Does offload authorization use the published reference? |
| 3. Cleanup gate and mutation | `workflow/controller/pod/status_capture.go`: `observePodCleanup`, `capturedDisposition`, `allowPodCleanup`; `pod/queue.go`: `processNextPodCleanupItem`, `getPodCleanupPatch`; `pod/cleanup_key.go` | Are fresh reads, node/task state, UID-bound requests and Pod mutation preconditions sufficient? Are foreign finalizers and replacements preserved? |
| 4. Recovery and retries | `workflow/controller/pod/recovery.go`: `ReconcilePodCleanup`, `QueueWorkflowCleanup`, `reconcilePodCleanup`; `pod/controller.go`; `workflow/controller/controller.go`; retry handling in `pod/queue.go` | Can initial events, completion/filter exit and transient failures recover work without stale authorization or an additional Pod event? |
| 5. Lifecycle dispositions | `workflow/controller/exec_control.go`: `handleExecutionControlError`; `workflow/controller/pod/workflow_cleanup.go`: `resolveWorkflowPodCleanup`; `pod/status_capture.go`: `restartDisposition`; `pod/cleanup.go`, `pod/accessors.go` | Do restart, stop/terminate, daemon, agent and owner-removal paths preserve their intended contracts? |
| 6. Legacy and operations | `workflow/controller/pod_legacy_capture.go`: `legacySuccessfulNode`, `recaptureLegacyPod`; `pod/legacy_capture.go`: `ensureCapturedDisposition`; `pod/status_capture_diagnostics.go`: `reportCleanupHold`; `hack/status-capture.py` | Is supported recapture same-result only, with authoritative readback? Are unsupported holds diagnosable? The offline helper exports evidence and prepares an explicit release patch; it neither calls the API nor proves capture. |

In table rows, `pod/...` abbreviates `workflow/controller/pod/...`.

### Why the patch has 61 paths

| Group | Paths | What to read |
|---|---:|---|
| Production Go | 16 | The route above: API field, result persistence, cleanup, recovery and lifecycle/legacy handling. |
| Tests and test support | 25 | Capture/offload/unknown-commit tests; replacement and concurrent-finalizer tests; real-queue retry/recovery tests; lifecycle and legacy tests; API wire round-trip; cost harnesses; offline-helper tests. `pod/testing.go` is test support despite its filename. |
| Generated schemas, manifests and model documentation | 12 | API JSON/OpenAPI schemas; full CRD and four quick-start manifests; protobuf/OpenAPI output; `docs/fields.md`; Java NodeStatus documentation. Check consistent field propagation and generated verification. |
| Offline helper | 1 | `hack/status-capture.py`, separately reviewable operator tooling. |
| Test automation | 2 | `Makefile` target `test-status-capture` and `.github/workflows/ci-build.yaml` job `status-capture-tests`. |
| Authored documentation and navigation | 5 | `docs/status-capture.md`, `docs/upgrading.md`, `docs/environment-variables.md`, feature-description entry and `properdocs.yml`. |

### Start with focused checks

Run from the full candidate checkout, not this presentation directory. These commands use the toolchain/build tag used for the recorded checks; consult [validation](validation.md) for scope and provenance.

```sh
export GOTOOLCHAIN=go1.26.5
export GOFLAGS='-mod=readonly -tags=kubernetes_protomessage_one_more_release'
go test ./workflow/controller/pod
go test ./workflow/controller -run '^(TestCapturedPod|TestLegacyCapture|TestLegacyCleanupCost|TestCleanupCost)'
go test ./pkg/apis/workflow/v1alpha1 -run '^TestCapturedPodUIDWireRoundTrip$'
make test-status-capture
GOMAXPROCS=2 go test ./workflow/hydrator -run '^$' \
  -bench '^BenchmarkWorkflowHydrationCost$' -benchmem -count=5
```

For the real controller comparison, follow [reproduction instructions](reproduction.md) using [the reproducer](reproduce.py). Compare [upstream observations](traces/baseline.jsonl) with [candidate observations](traces/candidate.jsonl), particularly the original Pod UID, persisted node phase/task state and Pod disappearance. A successful demo is one piece of the review; offload, replacement, crash and lifecycle checks require their own evidence.
