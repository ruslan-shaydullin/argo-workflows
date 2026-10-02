# Argo Workflows #17024 — capture before Pod cleanup

Review evidence for the proposed fix by Ruslan Shaydullin. This is a contribution review snapshot, not an Argo Workflows release.

- [Original report and reproduction by @jalvarezz13](https://github.com/argoproj/argo-workflows/issues/17024).
- [Implementation commit](https://github.com/ruslan-shaydullin/argo-workflows/commit/7fb9d4251f4af99e1bd02078d7fcfd8165eeefe2).
- [2½-minute captioned demonstration](snapshot/demo.mp4) and [text transcript](snapshot/transcript.md).
- [Reviewer guide](snapshot/reviewer-guide.md): connected persistence, cleanup and recovery paths, validation, costs and compatibility.
- [Portable reproduction](snapshot/reproduction.md), [recorded observations](snapshot/run-summary.json) and [validation scope](snapshot/validation.md).
- [Downloadable review assets](https://github.com/ruslan-shaydullin/argo-workflows/releases/tag/review-argo-17024-20261002).

The original successful Pod is lost by upstream under deliberately delayed Workflow reconciliation; the proposed controller retains it until the result can be persisted and the run finishes Succeeded. The demonstration is a replay of actual timestamped API reads, with waits condensed. It establishes the controlled before/after outcome, not production incidence or throughput.

## Snapshot provenance

The 39 files in `snapshot/` are byte-for-byte copies of the verified prepublication review bundle. Statements there about local-only status and unrun remote CI describe that earlier snapshot. Current publication and CI state belong to the upstream PR; this evidence does not imply maintainer acceptance.

Implementation base: `dadd69141c570fa678f7d51ee6decfe3fa77f109`. The committed source set is unchanged from the tested candidate (`50a6b953587fbf7eccdc6c61f0d7a0db1fcae87c699293104d6ed6298b6d60fd`, 3232 files). Git reorders the 61 file-diff blocks when producing a normal commit diff; each block is identical to the frozen standalone patch.

| Artifact | SHA-256 |
|---|---|
| Portable review archive | `82c340ce54e3ddeada4859d24cf7484a6fbdff759803a14b535bd83c88e65100` |
| Demo MP4 | `0ae4dbeb684de9f2d6170a6a8f8af992bff813abe2b35b5067c1b6324a9859a4` |
| Frozen standalone patch | `aeba17d588a6fb9434f4d66eeaa72bdc20313a895e6a7eb3476dd2f9c6d11614` |

Material review questions remain: additional reads with the flag off, whole-map hydration for retained encoded backlogs, and the narrow automatic recovery contract for completed legacy Workflows. See the guide before deploying. AI assistance and author responsibility are disclosed in the proposed PR description.
