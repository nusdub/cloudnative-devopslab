# Runbook: Availability SLO Slow Burn

## Meaning

The service is steadily consuming error budget over longer windows. This usually indicates a persistent but less explosive issue.

## Checks

- Review release history and app version metrics.
- Compare error ratio by endpoint and status.
- Check HPA, resource limits and node pressure.
- Inspect recent configuration changes.

## Action

Create an incident ticket, assign an owner, and decide whether to freeze releases until the burn rate returns to normal.
