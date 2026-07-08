-- MerQato AI Resort Website — Supabase schema
-- Provision in the Supabase SQL editor (or `supabase db push`).
-- Every table is scoped by resortId so the platform can serve many resorts.

create extension if not exists vector;

create table if not exists resort_profile (
  id text primary key,
  name text not null,
  tagline text,
  description text,
  location text,
  heroImageUrl text,
  contactEmail text,
  contactPhone text,
  amenities text[],
  policies text,
  faqs jsonb default '[]',
  rooms jsonb default '[]',
  tours jsonb default '[]',
  restaurants jsonb default '[]',
  transport jsonb,
  emergencyContacts jsonb default '[]',
  updatedAt timestamptz default now()
);

create table if not exists inquiries (
  id text primary key,
  resortId text not null references resort_profile(id),
  name text not null,
  email text not null,
  message text not null,
  checkIn text,
  checkOut text,
  guests int,
  status text default 'new',
  createdAt timestamptz default now()
);
create index if not exists inquiries_resort on inquiries(resortId, createdAt desc);

create table if not exists bookings (
  id text primary key,
  resortId text not null references resort_profile(id),
  guestName text not null,
  roomId text not null,
  checkIn text not null,
  checkOut text not null,
  guests int not null,
  status text default 'pending',
  createdAt timestamptz default now()
);
create index if not exists bookings_resort on bookings(resortId, createdAt desc);

create table if not exists tasks (
  id text primary key,
  resortId text not null references resort_profile(id),
  type text not null,
  title text not null,
  description text,
  status text default 'todo',
  assignee text,
  due text,
  createdAt timestamptz default now()
);
create index if not exists tasks_resort on tasks(resortId, createdAt desc);

create table if not exists approvals (
  id text primary key,
  resortId text not null references resort_profile(id),
  action text not null,
  description text,
  requestedBy text,
  status text default 'pending',
  createdAt timestamptz default now()
);
create index if not exists approvals_resort on approvals(resortId, createdAt desc);

create table if not exists blog_posts (
  id text primary key,
  resortId text not null references resort_profile(id),
  title text not null,
  slug text not null,
  excerpt text,
  body text,
  published boolean default false,
  createdAt timestamptz default now()
);
create index if not exists blog_resort on blog_posts(resortId, createdAt desc);

create table if not exists ai_chats (
  id text primary key,
  resortId text not null references resort_profile(id),
  guestName text,
  message text not null,
  response text,
  escalated boolean default false,
  createdAt timestamptz default now()
);
create index if not exists aichats_resort on ai_chats(resortId, createdAt desc);

-- Knowledge base with pgvector for semantic search.
create table if not exists kb_entries (
  id text primary key,
  resortId text not null references resort_profile(id),
  category text,
  title text,
  content text,
  embedding vector(1536),
  createdAt timestamptz default now()
);
create index if not exists kb_resort on kb_entries(resortId);

-- Enable Row Level Security; configure policies per deployment.
alter table resort_profile enable row level security;
alter table inquiries enable row level security;
alter table bookings enable row level security;
alter table tasks enable row level security;
alter table approvals enable row level security;
alter table blog_posts enable row level security;
alter table ai_chats enable row level security;
alter table kb_entries enable row level security;

-- =============================================================================
-- MULTI-TENANT KNOWLEDGE INGESTION FOUNDATION
-- -----------------------------------------------------------------------------
-- Source of truth for tenant knowledge. Tenant identity uses an internal UUID
-- plus a unique, normalized human-readable slug for routing and CLI input.
-- Document content is immutable: each edit creates a new tenant_knowledge_versions
-- row. Versions are never UPDATEd in place (no overwrite of factual history).
-- Only verified + published + guest_visible + non-internal versions may be
-- indexed into Qdrant for guest retrieval.
-- =============================================================================

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
  -- internal-only facts must never be guest-visible
  check (not (internal_only = true and guest_visible = true)),
  -- published_at may only represent a verified version
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

-- F. indexes -----------------------------------------------------------------
create index if not exists tenants_slug_idx on tenants(slug);
create index if not exists tkd_tenant_idx on tenant_knowledge_documents(tenant_id);
create index if not exists tkv_tenant_idx on tenant_knowledge_versions(tenant_id);
create index if not exists tkv_verification_idx on tenant_knowledge_versions(verification_status);
create index if not exists kij_tenant_idx on knowledge_ingestion_jobs(tenant_id);
create index if not exists kal_tenant_idx on knowledge_audit_logs(tenant_id);

-- G. Row Level Security
-- These tables are accessed by the FastAPI service using the SERVICE ROLE key,
-- which bypasses RLS. Tenant-owned tables have RLS enabled as defense-in-depth.
-- Normal browser clients must NEVER receive service-role credentials; they reach
-- data only through the FastAPI BFF. Policies below permit service-role access.
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

-- Expand the category allowlist to the ten supported knowledge categories.
-- Idempotent: only adjusts an existing table whose constraint still lists the
-- original five categories. Safe to re-run on fresh or already-migrated schemas.
do $$
begin
  if exists (
    select 1 from information_schema.check_constraints cc
    join information_schema.constraint_column_usage ccu
      on cc.constraint_name = ccu.constraint_name
    where cc.constraint_schema = 'public'
      and ccu.table_name = 'tenant_knowledge_documents'
      and ccu.column_name = 'category'
      and cc.check_clause like '%''transport''%'
      and cc.check_clause not like '%''rooms''%'
  ) then
    alter table tenant_knowledge_documents
      drop constraint if exists tenant_knowledge_documents_category_check;
    alter table tenant_knowledge_documents
      add constraint tenant_knowledge_documents_category_check
        check (category in (
          'identity', 'rooms', 'rates', 'amenities', 'policies',
          'wifi_power', 'food_breakfast', 'transport', 'emergency_contacts', 'faq'
        ));
  end if;
end $$;

