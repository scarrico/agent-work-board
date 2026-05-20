# Work Queue Strategies

The Kanban board supports the strategy pattern for work selection. All workers
call the same method:

```python
card = board.claim_next(worker_id="worker-01", strategy="priority_fifo")
```

The strategy decides which claimable card comes next.

## Built-In Strategies

| Strategy | Behavior | Useful For |
| --- | --- | --- |
| `priority_fifo` | Highest priority first, oldest update wins ties | Default production queue |
| `fifo` | Oldest update first | Fair simple queues |
| `lifo` | Newest update first | Interactive/demo workflows |
| `retry_first` | Failed/attempted work first | Clearing retries before new work |
| `fresh_first` | Untouched work first | Avoiding repeated failures during broad sweeps |

## Why This Matters for Agents

Different agent swarms want different behavior:

- ticker workers may want `priority_fifo`
- recovery agents may want `retry_first`
- exploratory agents may want `fresh_first`
- UI demos may want `lifo` because new cards move immediately

The persistence backend does not need to know why a strategy was chosen. It only
needs to apply the strategy safely while claiming a card.

## Future Strategies

Good paid or advanced strategies:

- deadline first
- oldest lease expired first
- held-position tickers first
- sector-balanced ticker selection
- worker-affinity routing
- cost-aware provider routing
- human escalation first
