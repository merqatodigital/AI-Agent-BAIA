# MerQato BAIA Knowledge and Skills v1.2.0

This release replaces the earlier partially verified BAIA fixture set with the user-provided verified operational breakdown.

## Ingestion contract

- Filename stem becomes the database `category`.
- The full root JSON object becomes the database `content` JSONB.
- Do not expect `content[category]`.
- No redundant top-level category wrapper is used.

## Boundaries

- `fixtures/baia-resort/` contains factual BAIA data only (tenant slug `baia-resort`).
- `skills/` contains behavioral requirements for the CrewAI concierge only.
- Shared San Vicente knowledge (`knowledge/shared/san_vicente/`) remains separate from BAIA tenant facts.

## v1.2 Regional expansion

Added Poblacion, Alimanguan, Port Barton, surfing, island hopping, and waterfall knowledge for guest recommendations.

## v1.2 corrections

- README title corrected from v1.1 to v1.2.0.
- Fixture `tenant_slug` corrected from `baia_resort` to `baia-resort` to match the canonical platform tenant slug.
