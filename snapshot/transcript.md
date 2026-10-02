# Argo Workflows #17024 — recorded API replay

Silent, captioned, 2:30 demonstration. Waits are condensed. Panels are aligned by experiment phase. API reads are sequential and not atomic. Different runs have different Pod UIDs.

One controlled ordinary-Pod scenario per version, not a production frequency or latency benchmark. Both variants use the candidate CRD schema. The baseline binary does not write capturedPodUID.

## 00:00–00:09 — Observed outcome

Both workloads completed successfully. Upstream ended with Workflow Error; the proposed controller ended Succeeded. This is one controlled ordering experiment per version.

- `traces/baseline.jsonl` line 305; record SHA-256 `c344717bf9e9d8cbdce3ac45d9814646a40b2be42e1790c6168104bfdf8b4d22`.
  Pod read 2026-10-01T21:01:05.454125+00:00 (+260.880s); Workflow read 2026-10-01T21:01:05.505697+00:00 (+260.931s).
- `traces/candidate.jsonl` line 351; record SHA-256 `a4b9794bff8e0f4c57570267f1b3b7cc2eeb1b1188055cfb5eb0c75983f62eb6`.
  Pod read 2026-10-01T21:01:45.157526+00:00 (+300.583s); Workflow read 2026-10-01T21:01:45.207867+00:00 (+300.633s).

## 00:09–00:20 — Controlled experiment

Status capture enabled. Separate runs and Pod identities. Stop the controller; wait for successful workload completion; age the Pod 190 seconds; request deletion; run cleanup with zero Workflow workers. Candidate is held for 40 seconds in this phase; upstream resumes after observing Pod loss. Resume reconciliation. Setup does not patch Workflow status or Pod finalizers.


## 00:20–00:33 — The workload finished; the controller is paused

Both Pod APIs report Succeeded; the stored Workflow still reports Running. These are separate persisted resources. Successful execution alone does not settle the Workflow result.

- `traces/baseline.jsonl` line 79; record SHA-256 `fadaedeccd0f84b90ed0336cf49041ad210abf87ce9492626e55ad20ddcb1f33`.
  Pod read 2026-10-01T20:57:51.605718+00:00 (+67.025s); Workflow read 2026-10-01T20:57:51.650418+00:00 (+67.069s).
- `traces/candidate.jsonl` line 79; record SHA-256 `46b264f4632259d6ae74db5d890dc98094e2d2d1850ce4275e6b3c70e58f2915`.
  Pod read 2026-10-01T20:57:51.613626+00:00 (+67.032s); Workflow read 2026-10-01T20:57:51.661129+00:00 (+67.080s).

## 00:33–00:46 — Deletion is requested before result capture

The Pod carries a deletion timestamp and the status-capture finalizer. The Workflow result is still Running at the selected reads.

- `traces/baseline.jsonl` line 300; record SHA-256 `9754405334c3ecc175169fbecc3bae39c1ba0980cb6aeb78dcee532adf0a595f`.
  Pod read 2026-10-01T21:01:01.163365+00:00 (+256.589s); Workflow read 2026-10-01T21:01:01.211340+00:00 (+256.637s).
- `traces/baseline.jsonl` line 79; record SHA-256 `fadaedeccd0f84b90ed0336cf49041ad210abf87ce9492626e55ad20ddcb1f33`.
  Pod read 2026-10-01T20:57:51.605718+00:00 (+67.025s); Workflow read 2026-10-01T20:57:51.650418+00:00 (+67.069s).
- `traces/candidate.jsonl` line 300; record SHA-256 `0793cebbfcebda16d9fe7ecf96013e1fa04f832523cb3ada321b1cd98cf00f42`.
  Pod read 2026-10-01T21:01:01.160690+00:00 (+256.586s); Workflow read 2026-10-01T21:01:01.202726+00:00 (+256.628s).
- `traces/candidate.jsonl` line 79; record SHA-256 `46b264f4632259d6ae74db5d890dc98094e2d2d1850ce4275e6b3c70e58f2915`.
  Pod read 2026-10-01T20:57:51.613626+00:00 (+67.032s); Workflow read 2026-10-01T20:57:51.661129+00:00 (+67.080s).

## 00:46–01:00 — The cleanup-only attempt exposes the loss

Upstream has lost the Pod. Proposed still holds the completed Pod. Workflow workers remain at zero; the upstream controller has already been stopped after cleanup.

- `traces/baseline.jsonl` line 302; record SHA-256 `9f6bf9a2b3935e9781d0aa5578f92460d10135e03e320ceb84d9263524ca187a`.
  Pod read 2026-10-01T21:01:02.905087+00:00 (+258.331s); Workflow read 2026-10-01T21:01:02.953993+00:00 (+258.379s).
- `traces/baseline.jsonl` line 79; record SHA-256 `fadaedeccd0f84b90ed0336cf49041ad210abf87ce9492626e55ad20ddcb1f33`.
  Pod read 2026-10-01T20:57:51.605718+00:00 (+67.025s); Workflow read 2026-10-01T20:57:51.650418+00:00 (+67.069s).
- `traces/candidate.jsonl` line 347; record SHA-256 `00a6371916c3f5ec5892f9d48176bf4c5a1dc8d06d08b001897bc47528c6fc19`.
  Pod read 2026-10-01T21:01:41.712054+00:00 (+297.137s); Workflow read 2026-10-01T21:01:41.757668+00:00 (+297.183s).
- `traces/candidate.jsonl` line 79; record SHA-256 `46b264f4632259d6ae74db5d890dc98094e2d2d1850ce4275e6b3c70e58f2915`.
  Pod read 2026-10-01T20:57:51.613626+00:00 (+67.032s); Workflow read 2026-10-01T20:57:51.661129+00:00 (+67.080s).

## 01:00–01:13 — Resume upstream: the Workflow reports Error

Resume upstream: the Workflow reports Error. Pod Succeeded earlier; Workflow Error with pod deleted after resume.

- `traces/baseline.jsonl` line 305; record SHA-256 `c344717bf9e9d8cbdce3ac45d9814646a40b2be42e1790c6168104bfdf8b4d22`.
  Pod read 2026-10-01T21:01:05.454125+00:00 (+260.880s); Workflow read 2026-10-01T21:01:05.505697+00:00 (+260.931s).
- `traces/baseline.jsonl` line 79; record SHA-256 `fadaedeccd0f84b90ed0336cf49041ad210abf87ce9492626e55ad20ddcb1f33`.
  Pod read 2026-10-01T20:57:51.605718+00:00 (+67.025s); Workflow read 2026-10-01T20:57:51.650418+00:00 (+67.069s).

## 01:13–01:25 — Resume proposed: the result is persisted for this UID

Resume proposed: the result is persisted for this UID. Persisted Succeeded with taskResultSynced true and matching original capturedPodUID; a separate Pod API read reports absence. These reads are not atomic.

- `traces/candidate.jsonl` line 351; record SHA-256 `a4b9794bff8e0f4c57570267f1b3b7cc2eeb1b1188055cfb5eb0c75983f62eb6`.
  Pod read 2026-10-01T21:01:45.157526+00:00 (+300.583s); Workflow read 2026-10-01T21:01:45.207867+00:00 (+300.633s).
- `traces/candidate.jsonl` line 79; record SHA-256 `46b264f4632259d6ae74db5d890dc98094e2d2d1850ce4275e6b3c70e58f2915`.
  Pod read 2026-10-01T20:57:51.613626+00:00 (+67.032s); Workflow read 2026-10-01T20:57:51.661129+00:00 (+67.080s).

## 01:25–01:38 — Final comparison

Final outcome comparison: Error upstream, Succeeded proposed with matching original UID. Both final Pod reads report absence. Different runs have different Pod UIDs.

- `traces/baseline.jsonl` line 305; record SHA-256 `c344717bf9e9d8cbdce3ac45d9814646a40b2be42e1790c6168104bfdf8b4d22`.
  Pod read 2026-10-01T21:01:05.454125+00:00 (+260.880s); Workflow read 2026-10-01T21:01:05.505697+00:00 (+260.931s).
- `traces/baseline.jsonl` line 79; record SHA-256 `fadaedeccd0f84b90ed0336cf49041ad210abf87ce9492626e55ad20ddcb1f33`.
  Pod read 2026-10-01T20:57:51.605718+00:00 (+67.025s); Workflow read 2026-10-01T20:57:51.650418+00:00 (+67.069s).
- `traces/candidate.jsonl` line 351; record SHA-256 `a4b9794bff8e0f4c57570267f1b3b7cc2eeb1b1188055cfb5eb0c75983f62eb6`.
  Pod read 2026-10-01T21:01:45.157526+00:00 (+300.583s); Workflow read 2026-10-01T21:01:45.207867+00:00 (+300.633s).
- `traces/candidate.jsonl` line 79; record SHA-256 `46b264f4632259d6ae74db5d890dc98094e2d2d1850ce4275e6b3c70e58f2915`.
  Pod read 2026-10-01T20:57:51.613626+00:00 (+67.032s); Workflow read 2026-10-01T20:57:51.661129+00:00 (+67.080s).

## 01:38–01:53 — Protocol design

Design diagram, not an observation timeline: capture exact Pod UID; persist result and offload reference where used; read fresh proof; release checked Pod finalizer. Uncertainty retains the finalizer; restart rediscovers cleanup. This demo does not exercise every supported path.


## 01:53–02:06 — Tradeoffs

Extra reads remain with flag off. Whole-map legacy hydration remains costly. Ordinary completed two-step legacy workflows are not automatically recaptured. No production frequency or latency claim, and no claim that this demo covers every lifecycle or offload path.


## 02:06–02:20 — Reviewer route

Three reading depths: replay for the outcome; PR description and costs for design; reviewer-guide and reproduction instructions for deep review. Exact source lines, timestamps and SHA-256 hashes are recorded in scenes.json. Text alternative in transcript.md.


## 02:20–02:30 — Closing

Preserve the result before allowing cleanup. Observed upstream Error; observed proposed Succeeded with original captured Pod UID. Review persisted proof, Pod identity, legacy and rollout behavior, and cost. Local candidate, not merged.

- `traces/baseline.jsonl` line 305; record SHA-256 `c344717bf9e9d8cbdce3ac45d9814646a40b2be42e1790c6168104bfdf8b4d22`.
  Pod read 2026-10-01T21:01:05.454125+00:00 (+260.880s); Workflow read 2026-10-01T21:01:05.505697+00:00 (+260.931s).
- `traces/candidate.jsonl` line 351; record SHA-256 `a4b9794bff8e0f4c57570267f1b3b7cc2eeb1b1188055cfb5eb0c75983f62eb6`.
  Pod read 2026-10-01T21:01:45.157526+00:00 (+300.583s); Workflow read 2026-10-01T21:01:45.207867+00:00 (+300.633s).

