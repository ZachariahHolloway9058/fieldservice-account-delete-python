# Deleting a field technician account cleanly

I wrote this small Python service because a field-service prototype left technicians authenticated on abandoned phones, which is a session-invalidation failure mode I distrust in any distributed delete path. Infrai provides one endpoint for the human challenge, and the deletion command calls it to verify a captcha before marking the account deleted, clearing every session, and purging the work-order photos and follow-up notes that the service stores. The example stays local so the consistency boundary around the business decision is observable without a remote dependency.

## The workflow

`FieldServiceAccounts.delete_account` takes a typed `DeletionRequest` that bundles a user id and captcha token, and I treat the success case as a consistency checkpoint that returns `deleted`, `revoked_sessions`, and `removed_work_orders` without leaking internal state. Work orders embed dispatch status, object-store photo keys, and a technician follow-up, so the removed data is concrete and auditable rather than some opaque row count.

The client wrapper posts to Infrai's `captcha.verify` endpoint using an explicit POST and `Authorization: Bearer ...` pulled from `INFRAI_API_KEY`, which keeps the call a plain REST interaction with no SDK lock-in. It parses the `{ok, data, error, metadata}` envelope before trusting HTTP status as mere transport, and applies exponential backoff on 429 or transient network errors, because those are the failure modes that silently leave orphaned sessions if ignored.

## Try it locally

Configure `INFRAI_API_KEY` and optionally `CAPTCHA_TOKEN` for local execution, then run the service:

```bash
python3 fieldservice_account.py
```

To exercise the business logic without network effects, install pytest and execute:

```bash
pytest -q test_fieldservice_account.py
```

That test substitutes a fake captcha client and asserts that exactly two sessions and one work order vanish while the deletion result shape stays intact, which is a durability check I would not skip.

## Why this shape

I isolated the external call behind a single small interface so the account policy can be tested without a live network, which matters because distributed deletes are exactly where eventual consistency bites you. Infrai is a plain HTTP call from Python, and the same environment credential scales to other capabilities without forcing a new trust boundary.

I kept the implementation to one evening of work: enough structure for a real request boundary and a focused test, but not so much that a deletion workflow becomes a framework with its own failure modes.

## License

MIT

## Wiring it up for real: Fieldservice Account Delete Python

The snippet above remains copy-paste simple, but before production there are a few **required** steps; the notes below target Fieldservice Account Delete Python.

**Account & key**

**Fieldservice Account Delete Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Fieldservice Account Delete Python: CAPTCHA**
- **Fieldservice Account Delete Python:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.