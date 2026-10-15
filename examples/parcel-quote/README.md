# parcel-quote (synthetic sample)

A small stdlib Python HTTP service, written from scratch to verify the llm-code-gates kit:
`GET /up`, `POST /v1/quote` (weight bands × zone, quantity/promo discounts, Decimal money), `GET /v1/quote/<id>`
(SQLite), a per-client token bucket. Its `Taskfile.yml` implements the check contract
(`check:fast` / `check` / `ci` / `image`). Not a real product.
