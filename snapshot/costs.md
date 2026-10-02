# Cost of the proposed capture guarantee

This compares upstream `dadd69141c570fa678f7d51ee6decfe3fa77f109` with the proposed patch. The [213 recorded scenarios](evidence/cost-comparison.json) include counters, payload sizes and resulting Pod states. They are a projection of the previously completed measurement run; producing the demonstration did not rerun the cost suite.

`P/W/H` means Pod GET / Workflow GET / full encoded-node hydration. Counts cover actual event handlers, queue and workers with fake API counters and the production hydrator. Informer startup LIST/WATCH and unrelated Workflow reconciliation are excluded. Offload hydration counts a logical repository Get, not an observed SQL statement or network latency.

| Work unit | Upstream P/W/H | Proposed P/W/H | Behavior / other work |
|---|---|---|---|
| Active raw Pod; one Add or significant Update; either flag | 0/0/0 | 1/1/0 | Same active Pod; no mutation or idle polling |
| Active compressed/offloaded Pod; same unit; either flag | 0/0/0 | 1/1/1 | Same active Pod; no mutation or idle polling |
| Captured terminal encoded Pod; recovery through mutation; flag on | 0/0/0; recovery absent | 2/2/2 | Proposed: one guarded Pod PATCH |
| Captured terminal offloaded Pod; same path; flag off | 0/0/0; recovery absent | 2/1/1 | Proposed: one guarded Pod PATCH |
| Initial pass: 16 unsupported completed-legacy Pods of one encoded Workflow; flag on | 0/0/0 + 16 finalizer PATCHes | 16/16/16; no writes | Upstream removes barriers without capture proof; proposed retains them |
| Supported one-node offloaded legacy; recapture through cleanup | 0/0/0 + 1 finalizer PATCH | 3/5/5 | Proposed: one logical Save, one Workflow Update and one Pod PATCH |

Rows with different behavior are not equal-work performance comparisons. A measured stable retry cycle for the same 16-Pod retained backlog costs 16/16/16; upstream has no corresponding cycle. One completion sweep adds a scoped Pod LIST. Some raw rows are cumulative initial-plus-retry observations; use their `key` when calculating per-cycle values.

The fresh read for an observation is reused within that observation. A separately queued mutation reads independently before acting. Encoded state is needed even for active Pods because persisted restart/daemon/stop dispositions live in nodes. Flag off does not remove those common obligations.

## Remaining hydration cost

For sixteen decodes of the same synthetic 1,025-node map, controlled in-process measurements were:

| Representation | Median elapsed work [min–max] | Allocated bytes |
|---|---|---:|
| Compressed | 95.041 ms [90.685–97.126] | 167,594,177 |
| Offload payload | 77.760 ms [75.006–82.114] | 40,991,923 |

These timings came from the earlier candidate and apply through an unchanged 124-file production dependency closure; the final decoder was not retimed. Go 1.26.5, Apple M4 Pro, `GOMAXPROCS=2`; no API/network/SQL latency. Allocation traffic is not peak memory. The synthetic payload is deliberately compressible. The patch reduces duplicate reads; it does not establish a faster decoder or acceptable production QPS.

## Re-run the in-tree checks

From the patched checkout:

```sh
export GOTOOLCHAIN=go1.26.5
export GOFLAGS='-mod=readonly -tags=kubernetes_protomessage_one_more_release'
GOMAXPROCS=2 KUBECONFIG=/dev/null go test -p 2 -count=1 -v \
  ./workflow/controller/pod ./workflow/controller \
  -run '^(TestCleanupCost|TestLegacyCleanupCost)'
GOMAXPROCS=2 KUBECONFIG=/dev/null go test -p 2 ./workflow/hydrator \
  -run '^$' -bench '^BenchmarkWorkflowHydrationCost$' \
  -benchmem -benchtime=1s -count=5
```

`COST_RESULT` records expose counters, exact fixture sizes and outcomes. The upstream rows were produced with baseline measurement overlays; these commands execute the candidate's in-tree tests, not the entire historical comparison. See [validation scope](validation.md).
