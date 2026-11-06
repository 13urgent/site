# Buffer publication adapter

This component does not run a service or create a daily scheduler. The calling
workflow must provide a future dated plan, public media and persisted state.

The only credential source is `BUFFER_API_KEY` in the process environment. No
credential values or Buffer account emails are queried or written to reports.
Queried organization/channel IDs and account names remain in memory. Persisted
state and reports contain a SHA-256 fingerprint instead of raw Buffer post IDs;
reports expose only connected services, never queried names or IDs.
Exact normalized channel names are allowlisted: Haeckel Hamri / LinkedIn,
Chronos / LinkedIn and 13urgentsite / TikTok. Ambiguous matches stop execution.

Read-only connection check:

```sh
python buffer_publish.py --mode probe --state state/state.json --output probe.json
```

Publication after supplying a plan:

```sh
python buffer_publish.py --mode publish --plan plan.json --state state/state.json --output publication.json --checkpoint-command 'python pipeline.py checkpoint --state-dir state'
```

A plan has `posts`, an array of objects with `id`, `channel_name`, `service`,
`text`, `video_url` and timezone-qualified `due_at`. The id must be stable between
reruns. TikTok requires video. Video delivery uses an owned public HTTPS URL.

The scheduler must serialize all runs. Every mutation is preceded by a durable
local intent AND, when supplied, a successful remote checkpoint command. A timeout
or malformed response quarantines that intent as uncertain. Reruns never recreate
an existing id, including when the runner died after Buffer accepted the post.
An uncertain/rejected record requires manual reconciliation against Buffer; do
not delete it or automatically assign a new id to bypass the quarantine.

A successful create response verifies `status` and `schedulingType`: only an
automatic scheduled state is accepted, with `dueAt` matching the requested instant
within one second, independently of timezone representation. A draft, approval request or notification
is saved as `provider_not_scheduled`, never retried automatically. Scheduling does
not prove successful delivery to LinkedIn/TikTok. `BufferClient.post_status(id)`
supports the officially documented read-only `post(input:{id})` query, returning
only lifecycle data. Native TikTok metadata requirements or channel permissions
can still cause rejection. Start with probe, then verify the first scheduled post
and its eventual delivery. A different due date is quarantined rather than retried.

Delivery reconciliation (read-only Buffer API calls):

```sh
python buffer_publish.py --mode verify --state state/state.json --output verification.json --checkpoint-command 'python pipeline.py checkpoint --state-dir state'
```

This reads up to five pages of 20 posts for the allowlisted channels, newest first,
and compares SHA-256 post IDs to the ledger. Known records become `sent` or
`delivery_error` according to Buffer; other people's existing posts are ignored.
Reports contain aggregate counts only. `scan_complete: false` explicitly means the
100-post scan cap was reached. Raw account/channel/post IDs are never persisted.
No new publication is created by verification. Unknown/ambiguous mutation intents
without a returned Buffer post ID remain quarantined for manual reconciliation.

Verified public API references: Buffer authentication, your-first-post and
hosting-media guides in the project documentation cache. Mutation fields and
success/error unions follow these examples. No live Buffer call was made during
development. The tests use fake responses and timeouts, without credentials.

Run tests: `python -m unittest -v test_buffer_publish.py`.
