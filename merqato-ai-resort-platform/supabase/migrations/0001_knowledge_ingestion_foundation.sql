-- =============================================================================
-- 0001_knowledge_ingestion_foundation
-- MerQato AI Resort Platform — multi-tenant knowledge ingestion foundation
-- -----------------------------------------------------------------------------
-- APPLY MODE: additive, idempotent, non-destructive.
--   * Safe to run on a fresh OR already-migrated project (all objects use
--     IF NOT EXISTS / CREATE ... IF NOT EXISTS / idempotent ALTER).
--   * No DROP, no TRUNCATE, no DELETE, no column type change that loses data.
--   * Re-running this file is a no-op for objects that already exist.
--
-- WHAT THIS CREATES (5 tables + indexes + RLS + service-role policies):
--   tenants                       tenant identity (UUID + unique slug)
--   tenant_knowledge_documents   stable logical document per (tenant, category)
--   tenant_knowledge_versions    immutable factual version history
--   knowledge_ingestion_jobs     Qdrant/ingestion job ledger (never auto-indexes)
--   knowledge_audit_logs         append-only audit trail
--
-- CONTRACT NOTES:
--   * Document content is immutable: every edit inserts a NEW
--     tenant_knowledge_versions row (never UPDATEd in place).
--   * Only VERIFIED + published + guest_visible + non-internal versions may
--     later be indexed into Qdrant. This migration creates NO Qdrant data.
--   * The backend service uses the SERVICE ROLE key, which BYPASSES RLS.
--     RLS is enabled as defense-in-depth; the policies below permit
--     service-role full access. Browser clients never receive that key.
-- =============================================================================

-- Enable the vector extension only if missing (required by future semantic
-- indexing; not used by this migration's writes).
create extension if not exists vector;

-- A. tenants -----------------------------------------------------------------
create table if not exists tenants (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  business_name text not null,
  business_type text not null,
  status text not null default 'draft'
    check (status in ('draft', 'active', 'suspended', 'archived')),
  primary_domain text,
  widget_token_hash text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- B. tenant_knowledge_documents (stable logical document) --------------------
create table if not exists tenant_knowledge_documents (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  category text not null
    check (category in (
      'identity', 'rooms', 'rates', 'amenities', 'policies',
      'wifi_power', 'food_breakfast', 'transport', 'emergency_contacts', 'faq'
    )),
  source_type text not null
    check (source_type in ('json_fixture', 'json_upload', 'dashboard_form', 'api_import')),
  source_filename text,
  current_version int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, category)
);

-- C. tenant_knowledge_versions (immutable factual history) -------------------
create table if not exists tenant_knowledge_versions (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references tenant_knowledge_documents(id) on delete cascade,
  tenant_id uuid not null references tenants(id) on delete cascade,
  version int not null,
  content jsonb not null,
  checksum text not null,
  verification_status text not null
    check (verification_status in ('draft', 'verified', 'rejected', 'archived')),
  guest_visible boolean not null default true,
  internal_only boolean not null default false,
  approved_by uuid,
  approved_at timestamptz,
  published_at timestamptz,
  created_at timestamptz not null default now(),
  unique (document_id, version),
  unique (tenant_id, checksum),
  -- Internal-only facts must never be exposed to guests.
  check (not (internal_only = true and guest_visible = true)),
  -- A published_at timestamp may only accompany a verified version.
  check (published_at is null or verification_status = 'verified')
);

-- D. knowledge_ingestion_jobs ------------------------------------------------
create table if not exists knowledge_ingestion_jobs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  document_version_id uuid references tenant_knowledge_versions(id) on delete set null,
  status text not null
    check (status in ('pending', 'running', 'completed', 'failed', 'skipped')),
  source text not null,
  collection_name text,
  chunks_created int not null default 0,
  checksum text,
  error_message text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now()
);

-- E. knowledge_audit_logs ----------------------------------------------------
create table if not exists knowledge_audit_logs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  document_id uuid references tenant_knowledge_documents(id) on delete set null,
  document_version_id uuid references tenant_knowledge_versions(id) on delete set null,
  action text not null,
  actor_type text not null,
  actor_id text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- F. indexes (all additive) --------------------------------------------------
create index if not exists tenants_slug_idx on tenants(slug);
create index if not exists tkd_tenant_idx on tenant_knowledge_documents(tenant_id);
create index if not exists tkv_tenant_idx on tenant_knowledge_versions(tenant_id);
create index if not exists tkv_document_idx on tenant_knowledge_versions(document_id);
create index if not exists tkv_verification_idx
  on tenant_knowledge_versions(verification_status);
create index if not exists kij_tenant_idx on knowledge_ingestion_jobs(tenant_id);
create index if not exists kal_tenant_idx on knowledge_audit_logs(tenant_id);

-- G. Row Level Security (defense-in-depth; backend uses service role) --------
alter table tenants enable row level security;
alter table tenant_knowledge_documents enable row level security;
alter table tenant_knowledge_versions enable row level security;
alter table knowledge_ingestion_jobs enable row level security;
alter table knowledge_audit_logs enable row level security;

-- Service role bypasses RLS (used by the backend ingestion service).
create policy if not exists "service role full access on tenants"
  on tenants for all to service_role using (true) with check (true);
create policy if not exists "service role full access on tenant_knowledge_documents"
  on tenant_knowledge_documents for all to service_role using (true) with check (true);
create policy if not exists "service role full access on tenant_knowledge_versions"
  on tenant_knowledge_versions for all to service_role using (true) with check (true);
create policy if not exists "service role full access on knowledge_ingestion_jobs"
  on knowledge_ingestion_jobs for all to service_role using (true) with check (true);
create policy if not exists "service role full access on knowledge_audit_logs"
  on knowledge_audit_logs for all to service_role using (true) with check (true);

-- =============================================================================
-- END 0001_knowledge_ingestion_foundation
-- Verification queries (read-only; run after applying):
--   select table_name from information_schema.tables
--     where table_schema='public'
--       and table_name in ('tenants','tenant_knowledge_documents',
--                           'tenant_knowledge_versions','knowledge_ingestion_jobs',
--                           'knowledge_audit_logs');
--   select count(*) from information_schema.check_constraints
--     where check_clause like '%''emergency_contacts''%';  -- expect >= 1
-- =============================================================================
