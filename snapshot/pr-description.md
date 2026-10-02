Fixes #17024.

### Motivation

With Pod status capture enabled, an aged, successfully completed Pod can be deleted before its result reaches persisted Workflow status. Subsequent reconciliation reports `Error: pod deleted`, even though the Pod succeeded. The independent cleanup queue can remove the finalizer while Workflow reconciliation is delayed.

This change ties normal result cleanup to persisted capture for the exact Pod UID, and reconstructs pending cleanup after controller restart.

```text
Same successful Pod; Workflow reconciliation is delayed; deletion is requested.

Upstream:  Pod Succeeded → finalizer removed → Pod gone → Workflow Error
Proposed:  Pod Succeeded → finalizer retained → result persisted → cleanup
                                                        └─ Workflow Succeeded
```

The reproduction uses zero Workflow workers to control this ordering; it does not establish failure frequency under normal load. Thanks to @jalvarezz13 for the report and reproduction. This builds on #8783 and the persistence/cleanup work in #12413 and #14129.

### Modifications

The implementation connects three parts of the same protocol:

1. **Record capture:** persist optional `status.nodes[*].capturedPodUID` with the controller-selected result and applicable task state. For offloaded nodes, a saved row is insufficient until the Workflow publishes its reference.
2. **Guard cleanup:** read the current Workflow and selected node representation, check the result and Pod identity, and protect the Pod mutation with UID/resourceVersion preconditions.
3. **Resume cleanup:** rebuild pending work after restart and retry transient failures without requiring another Pod event.

Recording capture alone would leave deletion unguarded; guarding deletion without recovery could leave Pods held after a crash. Schema changes, cleanup and recovery therefore belong together. Owner deletion, verified absent/replaced owners, restart retirement, daemon/stop and agent cleanup keep their separate dispositions.

**Cost and compatibility:** the finalizer remains opt-in, but UID recording and common cleanup reads also run with the flag off. Completed legacy recovery is limited to a provable, unchanged single-root ordinary-container success. Even an ordinary two-step completed legacy Workflow is unsupported: its finalizers remain held, with diagnostics and an explicit operator procedure.

Measured event → queue → worker counts below are **Pod GET / Workflow GET / full encoded-node hydration**, against upstream base `dadd69141c570fa678f7d51ee6decfe3fa77f109`:

| Work unit | Upstream | Proposed |
|---|---|---|
| One active raw Pod hint, either flag | 0 / 0 / 0 | 1 / 1 / 0 |
| One active compressed/offloaded Pod hint, either flag | 0 / 0 / 0 | 1 / 1 / 1 |
| One captured encoded Pod, recovery through guarded cleanup, flag on | Recovery absent: 0 / 0 / 0 | 2 / 2 / 2, plus 1 Pod PATCH |
| Initial pass over 16 unsupported completed-legacy Pods of one encoded Workflow, flag on | 0 / 0 / 0, plus 16 finalizer PATCHes | 16 / 16 / 16; no writes, Pods retained |

The last two rows have different cleanup guarantees: upstream provides no equivalent recovery in the former and removes barriers without capture proof in the latter. A measured stable retry cycle for the same retained backlog costs 16 / 16 / 16; upstream has no corresponding retry cycle. Ordinary active Pods are not polled after their disposition. A completion sweep adds a scoped Pod LIST.

These are logical operation counts, excluding informer startup and unrelated reconciliation, not latency measurements. Offload hydration means a repository Get, not a measured SQL-query count. Whole-map hydration per retained Pod remains a cost; production throughput and latency are unmeasured.

### Verification

- The real-controller reproduction gives `Error: pod deleted` on upstream. Under the same controlled ordering, the candidate retains the original Pod UID, persists Succeeded and synchronized task state with that UID, then removes the Pod. Pod/Workflow status was not patched to manufacture either result.
- Actual API/PostgreSQL checks cover storage denial/restoration, the published offload reference, Pod replacement and deleting-owner cleanup.
- Local validation passed: the full Linux controller suite, complete Pod/hydrator/API race suites, affected root-controller race tests, 16 offline helper tests and `make pre-commit -B`. Helper tests have a dedicated CI job.

<details>
<summary>Run the focused regressions and cost measurements</summary>

```sh
export GOTOOLCHAIN=go1.26.5
export GOFLAGS='-mod=readonly -tags=kubernetes_protomessage_one_more_release'
go test ./workflow/controller/pod
go test ./workflow/controller -run '^(TestCapturedPod|TestLegacyCapture|TestLegacyCleanupCost|TestCleanupCost)'
GOMAXPROCS=2 go test ./workflow/hydrator -run '^$' \
  -bench '^BenchmarkWorkflowHydrationCost$' -benchmem -count=5
make test-status-capture
```

For the runtime comparison, use the isolated BusyBox/controller procedure in #17024: persist Running, stop the controller before workload completion, wait for a genuine Succeeded Pod and age its conditions, request deletion, restart with zero Workflow workers, then restore normal workers. Check the original Pod UID, persisted node result and cleanup ordering on both builds.

</details>

Remote GitHub CI has not run. Full repository-wide `make test`, full root-controller race and production load testing are outside the local validation scope.

### Documentation

Document capture semantics, legacy support, retained-Pod diagnosis and upgrade/rollback. Preserving outstanding capture obligations requires a preserving CRD and stopping old writers before the new controller runs; rollback requires resolving those obligations first and retaining the newer schema. This is not a blanket stop/drain requirement for every flag-off installation.

The offline helper exports evidence and prepares an explicit operator release patch; it does not call the API or assert capture. A feature-description entry and generated schema/model documentation accompany the change.

### AI

OpenAI Codex assisted with design, implementation, tests, documentation, experiments, review and this description. I have personally reviewed the prepared implementation. AI review does not replace my responsibility for the contribution.

<details>
<summary>PR checklist</summary>

See the [pull request guide](https://argo-workflows.readthedocs.io/en/latest/pull-requests/).

- [x] Ran `make pre-commit -B`
- [ ] Signed-off commits with Conventional Commit messages
- [ ] PR title is a conventional commit message (it becomes the release notes entry)
- [x] Unit or e2e tests cover the change
- [x] For features: an associated issue and a feature description file (`make feature-new`)
- [ ] Opened as draft; will mark "Ready for review" once builds are green

</details>
