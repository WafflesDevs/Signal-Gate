# Signal Gate × Supabase

## 1. Create project
1. Go to [supabase.com](https://supabase.com) → New project  
2. Copy **Project URL**, **anon public** key, and **service_role** key from **Settings → API**

## 2. Auth (users + email confirmation)
1. **Authentication → Providers → Email** → enable Email  
2. Turn **Confirm email** ON (users must verify before full access)  
3. **Authentication → URL Configuration**  
   - Site URL: `http://localhost:5173`  
   - Redirect URLs: `http://localhost:5173/**`

## 3. Brand the emails (icon + Signal Gate banner)
Templates live in [`email-templates/`](email-templates/).

1. **Storage → New bucket** named `branding` → set **Public**  
2. Upload [`frontend/public/signal-s.png`](../frontend/public/signal-s.png)  
3. Copy the public URL, e.g.  
   `https://YOUR_PROJECT.supabase.co/storage/v1/object/public/branding/signal-s.png`  
4. In each HTML file, replace every `LOGO_URL` with that URL  
5. **Authentication → Email Templates** — paste:

| Supabase template | File |
|---|---|
| Confirm signup | `email-templates/confirm-signup.html` |
| Magic Link | `email-templates/magic-link.html` |
| Reset password | `email-templates/reset-password.html` |
| Change email address | `email-templates/change-email.html` |

Also set subjects, for example:
- Confirm: `Verify your email — Signal Gate`
- Reset: `Reset your Signal Gate password`
- Magic: `Your Signal Gate magic link`

## 4. Database
Run [`schema.sql`](schema.sql) in **SQL Editor**.

This creates:
- `conversations` + `messages` (chat history)
- `alpaca_credentials` (per-user Alpaca API keys — **required for Settings**)

If you already ran an older schema, re-run the `alpaca_credentials` section at the bottom of `schema.sql`.

## 5. Env vars

Root `.env`:
```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Required to encrypt Alpaca secrets in Settings
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
CREDENTIALS_FERNET_KEY=your_fernet_key_here
```

`frontend/.env`:
```env
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
```

## 6. Run
```bash
# API
uvicorn app.main:app --reload --port 8000

# UI
cd frontend && npm run dev
```

Signup → check inbox → branded **Verify your email** → **Settings** → link Alpaca → Chat.
