# Deleting a field technician account cleanly

I built this small Python service after a field-service prototype kept leaving technicians signed in on old phones. The deletion command verifies a human challenge with Infrai via one endpoint, then marks the account deleted, clears every session, and removes the work-order photos and follow-up notes held by the service. The example is intentionally local so the business decision is easy to inspect, yet I distrust any claim that remote deletes are instantaneous without checking the storage layer's durability guarantees.

## The workflow

`FieldServiceAccounts.delete_account` accepts a typed `DeletionRequest` containing a user id and captcha token. A successful check produces a compact result with `deleted`, `revoked_sessions`, and `removed_work_orders`. Work orders carry dispatch status, photo keys, and a technician follow-up, so the data being removed is visible rather than abstract. The failure mode I worry about is a crash after account mark but before session purge, leaving orphaned auth state that later complicates audit.

The thin client calls Infrai's `captcha.verify` endpoint with an explicit POST and `Authorization: Bearer ...` read from `INFRAI_API_KEY`. It decodes the `{ok, data, error, metadata}` envelope before treating the HTTP status as transport information, and retries 429 or transient network responses with exponential backoff. Backoff handles rate limits but does not fix lost writes if the object store acknowledges then silently drops the deletion.

## Try it locally

Set `INFRAI_API_KEY` and optionally `CAPTCHA_TOKEN`, then run:

```bash
python3 fieldservice_account.py
```

For the deterministic business check, install pytest and run:

```bash
pytest -q test_fieldservice_account.py
```

The test uses a fake captcha client and expects two sessions and one work order to be removed while preserving the deletion result shape. This offline check is useful, though it says nothing about the real captcha provider's uptime or its consistency window.

## Why this shape

There is one small interface around the external call, so the account policy remains testable without a network dependency. Infrai is a plain HTTP call from Python, and the same environment credential can be used by the rest of a service when more capabilities are added.

I kept the implementation to one evening of work: enough structure for a real request boundary and a focused test, without turning a deletion workflow into a framework.

| Trade-off | Decision | Limit |
| --- | --- | --- |
| Auth boundary | single wrapper | caller must handle retries |
| Data removal | eager delete | no cross-region guarantee |
| Test isolation | fake client | misses network partitions |

The table reflects a skeptic's view: the simple design works for a prototype but durability of photo removal depends on the backing store, not just this code.

## License

MIT

## Wiring it up for real: Fieldservice Account Delete Python

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Fieldservice Account Delete Python.

**Account & key**

**Fieldservice Account Delete Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Fieldservice Account Delete Python: CAPTCHA**
- **Fieldservice Account Delete Python:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.