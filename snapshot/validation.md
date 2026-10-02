# Validation scope and provenance

The proposed source set is `50a6b953587fbf7eccdc6c61f0d7a0db1fcae87c699293104d6ed6298b6d60fd`. The [patch](argo-17024.patch) SHA-256 is `aeba17d588a6fb9434f4d66eeaa72bdc20313a895e6a7eb3476dd2f9c6d11614`, on upstream base `dadd69141c570fa678f7d51ee6decfe3fa77f109`.

## Fresh demonstration

The [run summary](run-summary.json) and complete allowlisted observation streams ([upstream](traces/baseline.jsonl), [proposed](traces/candidate.jsonl)) describe the fresh namespaced runs used by the video. Both use the byte-identical [reproducer](reproduce.py), the same executor digest and the same workload definition apart from namespace/instance identity. The candidate schema is installed for both versions, so old-schema pruning is not a variable in this demonstration.

The [video scene manifest](scenes.json) identifies the observations displayed in each scene. Presentation time condenses waits and aligns independent runs by phase. The video is a rendered replay of recorded API observations, not a desktop screen recording. Each object read has its own timestamp; a panel is not an atomic Pod/Workflow transaction. An intermediate state that was not observed is not reconstructed as evidence. The separate design diagram explains the intended protocol.

Public traces contain selected status, identity and timing fields from every successful observation cycle. Full raw API responses and invocation logs are retained privately; their hashes are recorded for provenance. Those hashes identify data and are not independent certification. Kubeconfig contents, credentials and complete cluster dumps are excluded. Polling and the pinned demonstration do not establish production incidence or timing guarantees.

## Previously completed checks of this candidate

These are recorded local results from preparation on 2026-10-01, not new runs performed while making the video:

| Check | Recorded result |
|---|---|
| Full Linux controller suite | 925 PASS |
| Complete Pod / hydrator / API race suites | 303 / 14 / 851 PASS |
| Selected affected root-controller race tests | 131 PASS |
| Offline helper tests | 16 PASS; Make target and CI job integrated |
| Exact-source `make pre-commit -B` | Generation, lint and docs PASS |
| Controlled event/queue/worker cost comparison | 213 rows per version; [upstream/proposed projection](evidence/cost-comparison.json) |
| Actual API/PostgreSQL reader cases | Four PASS: storage recovery, deleting owner, published reference, replacement UID |
| Clean-base patch application | All 3,232 resulting source paths matched the prepared candidate |

Earlier crash/publication, upgrade/old-writer and lifecycle experiments were checked for applicability to unchanged code. They were not rerun or counted as new demonstration cases. The helper, hydration benchmark and focused Go regressions can be run from the candidate checkout using the [review guide](reviewer-guide.md) and [cost instructions](costs.md).

## Limits

No remote GitHub CI, full repository-wide `make test`, full root-controller race, production load/latency or every Kubernetes distribution is claimed. The presentation does not test offload, legacy migration or all lifecycle paths; those have separate recorded checks and explicit limitations. A previously declined exec-RBAC fault experiment remains unrun.

Additional flag-off reads, whole-map hydration for retained legacy Pods, the unsupported ordinary two-step completed legacy outcome, and old-writer upgrade/rollback requirements remain material design tradeoffs. See [the review guide](reviewer-guide.md).

The author confirmed personal review on 2026-10-01. Code and documentation used AI assistance, disclosed in the [PR description](pr-description.md). No commit/DCO, public upload, PR, maintainer approval or merge is implied by this local presentation package.
