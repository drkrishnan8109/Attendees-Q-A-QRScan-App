# ADR-001: Use hosted PostgreSQL for persistent deployment storage

## Status

Accepted

## Date

2026-08-19

## Context

The app must preserve household data for six months while running on a free Streamlit host. Streamlit Community Cloud containers can restart, so their local filesystem is not the authoritative store. The data is relational and balance updates must be atomic.

## Decision

Use PostgreSQL through SQLAlchemy, with Supabase Free as the documented provider. Use Supabase's session pooler connection string when the deployment network needs IPv4. Keep a SQLite URL as a local-development fallback only.

## Alternatives considered

### SQLite on Streamlit Community Cloud

- Pros: no service or credentials.
- Cons: cloud-local files are not durable across restarts.
- Rejected: does not satisfy persistent storage.

### Supabase Data API

- Pros: HTTP-based and supported directly by Supabase.
- Cons: requires a second provider-specific data layer and careful RLS design.
- Rejected for v1: a standard server-side PostgreSQL connection keeps the app portable and simpler.

### Other free hosted PostgreSQL providers

- Pros: compatible with the same repository through a connection-string change.
- Cons: quotas and sleep behavior vary.
- Deferred: the implementation stays provider-neutral.

## Consequences

- The deployed app needs one secret PostgreSQL connection string.
- Local development works immediately with SQLite but is explicitly not a cloud persistence strategy.
- The free Supabase project may pause after inactivity and does not include automatic backups.
- Adding multi-user access later will require authentication and per-household authorization.

