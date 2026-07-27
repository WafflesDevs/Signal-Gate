# Signal Gate

<p align="center">
  <img src="frontend/public/signal-s.png" alt="Signal Gate" width="96" />
</p>

<p align="center">
  <strong>Crypto AI paper-trading desk — spoken in plain English.</strong><br/>
  Ask prices, research markets, and route paper or live orders through Alpaca — with a human gate before anything hits the wire.
</p>

<p align="center">
  <a href="https://github.com/WafflesDevs/Signal-Gate"><img src="https://img.shields.io/badge/repo-private-0d1117?style=flat-square" alt="Private repo" /></a>
  <img src="https://img.shields.io/badge/Alpaca-Trading%20API-00C805?style=flat-square" alt="Alpaca" />
  <img src="https://img.shields.io/badge/paper%20%2F%20live-HITL-22d3a6?style=flat-square" alt="HITL" />
  <img src="https://img.shields.io/badge/stack-FastAPI%20%2B%20React-38bdf8?style=flat-square" alt="Stack" />
</p>

---

## What it is

Signal Gate is a chat-first trading desk for crypto. You talk to an agent; it reads your book and the market, proposes trades, and **waits for your approve / reject** before sending orders through your linked **Alpaca Trading API** keys (paper or live).

No order leaves the desk without you.

---

## Features

- **Natural language trading** — “buy 0.5 ETH”, “sell all SOL” → precise paper (or live) orders
- **HITL gate** — every buy/sell pauses for your yes or no
- **Active trades** — track open positions and exits from the desk
- **Live candle charts** — timeframe switches on real bars while you chat
- **Market + research** — prices, portfolio context, and web research on demand
- **Alpaca rails** — paper practice or live funds; keys linked per user in Settings
- **Paper / live toggle** — same desk, matching Alpaca dashboard keys

---

## Screenshots

<p align="center">
  <img src="docs/screenshots/home.png" alt="Signal Gate home" width="820" />
  <br/><em>Home — desk hero, ticker, markets</em>
</p>

<p align="center">
  <img src="docs/screenshots/features.png" alt="Features — NL trading and HITL gate" width="820" />
  <br/><em>Features — natural language orders + approve gate</em>
</p>

<p align="center">
  <img src="docs/screenshots/features-faq.png" alt="FAQ" width="820" />
  <br/><em>FAQ — paper vs live, approval, charts</em>
</p>

<p align="center">
  <img src="docs/screenshots/login.png" alt="Login" width="820" />
  <br/><em>Login — welcome back to the desk</em>
</p>

<p align="center">
  <img src="docs/screenshots/splash.png" alt="Brand splash" width="820" />
  <br/><em>Brand transition</em>
</p>

Chat, Charts, and Active trades sit behind auth after you link Alpaca in Settings.

---

## Setup

### 1. Backend

```bash
cd "Signal Gate"
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# or: uv sync

cp .env.example .env
# fill keys — see Env vars below (never commit .env)

uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
cp .env.example .env
# set VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY

npm install
npm run dev
```

UI: [http://localhost:5173](http://localhost:5173) · API: [http://localhost:8000](http://localhost:8000)

### 3. Supabase

1. Create a project and copy URL + anon + service_role keys  
2. Enable Email auth (confirm email recommended)  
3. Run [`supabase/schema.sql`](supabase/schema.sql) in the SQL Editor  
4. Full walkthrough: [`supabase/README.md`](supabase/README.md)

### Env vars

**Root `.env`** — copy from [`.env.example`](.env.example):

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Agent / research |
| `TAVILY_API_KEY` | Web research |
| `CREDENTIALS_FERNET_KEY` | Encrypt per-user Alpaca secrets at rest |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | Auth + DB |
| `LANGSMITH_*` / `LANGCHAIN_*` | Optional tracing |

**`frontend/.env`** — copy from [`frontend/.env.example`](frontend/.env.example):

| Variable | Purpose |
|---|---|
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Public anon key |
| `VITE_API_BASE` | Leave empty in local dev (Vite proxies the API) |

> Do **not** put trading `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` in project env for the trading stack. Users link Paper or Live keys in **Settings**; secrets are stored encrypted per user.

---

## Tech stack

| Layer | Stack |
|---|---|
| API | FastAPI, Uvicorn, LangChain / LangGraph, Alpaca (`alpaca-py`) |
| UI | React, Vite, TypeScript, Framer Motion, Lightweight Charts |
| Auth / data | Supabase (Auth + Postgres) |
| Broker | Alpaca Trading API (paper + live) |

---

## Links

- **Repo** (private): [github.com/WafflesDevs/Signal-Gate](https://github.com/WafflesDevs/Signal-Gate)
- **Alpaca**: [alpaca.markets](https://alpaca.markets)
- **Supabase setup**: [`supabase/README.md`](supabase/README.md)

---

## Credit

Built by **[WafflesDevs](https://github.com/WafflesDevs)**  
[LinkedIn](https://www.linkedin.com/in/ayaanalii/) · [GitHub](https://github.com/WafflesDevs)

---

<p align="center">
  <sub>Paper-trading desk for education and experimentation. Not financial advice. Live trading uses your own capital and Alpaca’s terms.</sub>
</p>
