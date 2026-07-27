-- Signal Gate: conversations + messages (run in Supabase SQL Editor)

create extension if not exists "pgcrypto";

create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null default 'New chat',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations (id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists conversations_user_updated_idx
  on public.conversations (user_id, updated_at desc);

create index if not exists messages_conversation_created_idx
  on public.messages (conversation_id, created_at);

alter table public.conversations enable row level security;
alter table public.messages enable row level security;

-- Users can only access their own conversations
drop policy if exists "conversations_select_own" on public.conversations;
create policy "conversations_select_own"
  on public.conversations for select
  using (auth.uid() = user_id);

drop policy if exists "conversations_insert_own" on public.conversations;
create policy "conversations_insert_own"
  on public.conversations for insert
  with check (auth.uid() = user_id);

drop policy if exists "conversations_update_own" on public.conversations;
create policy "conversations_update_own"
  on public.conversations for update
  using (auth.uid() = user_id);

drop policy if exists "conversations_delete_own" on public.conversations;
create policy "conversations_delete_own"
  on public.conversations for delete
  using (auth.uid() = user_id);

-- Messages: only via owned conversations
drop policy if exists "messages_select_own" on public.messages;
create policy "messages_select_own"
  on public.messages for select
  using (
    exists (
      select 1 from public.conversations c
      where c.id = messages.conversation_id and c.user_id = auth.uid()
    )
  );

drop policy if exists "messages_insert_own" on public.messages;
create policy "messages_insert_own"
  on public.messages for insert
  with check (
    exists (
      select 1 from public.conversations c
      where c.id = messages.conversation_id and c.user_id = auth.uid()
    )
  );

drop policy if exists "messages_delete_own" on public.messages;
create policy "messages_delete_own"
  on public.messages for delete
  using (
    exists (
      select 1 from public.conversations c
      where c.id = messages.conversation_id and c.user_id = auth.uid()
    )
  );

-- ---------------------------------------------------------------------------
-- Alpaca credentials (per user). Backend encrypts api_secret with Fernet
-- (CREDENTIALS_FERNET_KEY) before write. Run this section if you already
-- applied the conversations/messages DDL earlier.
-- ---------------------------------------------------------------------------

create table if not exists public.alpaca_credentials (
  user_id uuid primary key references auth.users (id) on delete cascade,
  api_key_id text not null,
  api_secret_enc text not null,
  is_paper boolean not null default true,
  updated_at timestamptz not null default now()
);

alter table public.alpaca_credentials enable row level security;

-- Users may read their own row (secret is already encrypted; UI uses API status).
drop policy if exists "alpaca_credentials_select_own" on public.alpaca_credentials;
create policy "alpaca_credentials_select_own"
  on public.alpaca_credentials for select
  using (auth.uid() = user_id);

drop policy if exists "alpaca_credentials_insert_own" on public.alpaca_credentials;
create policy "alpaca_credentials_insert_own"
  on public.alpaca_credentials for insert
  with check (auth.uid() = user_id);

drop policy if exists "alpaca_credentials_update_own" on public.alpaca_credentials;
create policy "alpaca_credentials_update_own"
  on public.alpaca_credentials for update
  using (auth.uid() = user_id);

drop policy if exists "alpaca_credentials_delete_own" on public.alpaca_credentials;
create policy "alpaca_credentials_delete_own"
  on public.alpaca_credentials for delete
  using (auth.uid() = user_id);

-- Note: the FastAPI backend uses SUPABASE_SERVICE_ROLE_KEY and bypasses RLS
-- for encrypt/decrypt + upsert. Keep service role server-side only.
