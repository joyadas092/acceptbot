# AGENTS.md — AI Agent Orientation Guide
# RequestAcceptBot — Production Telegram Auto Join Request Manager

> **Read this first before touching any file.**
> This document is written for AI coding agents. It explains what every file does,
> where to find things, what patterns are used, and how to fix common issues.

---

## 1. PROJECT OVERVIEW

A production-grade Telegram bot that:
- **Auto-approves join requests** to groups/channels (immediately or after a delay)
- **Sends configurable welcome messages** with inline buttons
- **Broadcasts messages** to users via a persistent worker queue (paid feature)
- **Supports multiple admins** and **per-chat configuration**
- **Targets 1M+ users** — never loads all users into RAM, never creates one task per user

**Tech Stack:**
| Component | Technology |
|---|---|
| Bot framework | aiogram 3.x |
| Database | MongoDB 7 via Motor (async) |
| Cache / Locks / FSM | Redis 7 via aioredis |
| Language | Python 3.12+ |
| Config | Pydantic Settings v2 |
| Logging | structlog |
| Testing | pytest + pytest-asyncio |
| Container | Docker + docker-compose |
| HTTP (health) | aiohttp |
| Metrics | prometheus-client |
| Retry logic | tenacity |

---

## 2. DIRECTORY MAP — WHAT IS WHERE

```
RequestAcceptBot/
│
├── main.py                        ← Bot entry point (webhook prod / polling dev)
├── requirements.txt               ← All Python dependencies
├── .env.example                   ← Copy to .env, fill in secrets
├── Dockerfile                     ← Multi-stage build, non-root user
├── docker-compose.yml             ← bot + approval_worker + broadcast_worker + redis + mongodb
├── README.md                      ← Human-facing setup & usage docs
├── AGENTS.md                      ← THIS FILE — AI agent orientation
│
├── workers/                       ← Standalone process entry points
│   ├── run_approval_worker.py     ← Run: python workers/run_approval_worker.py
│   └── run_broadcast_worker.py    ← Run: python workers/run_broadcast_worker.py
│
├── app/
│   ├── core/                      ← Shared infrastructure (no business logic)
│   │   ├── config.py              ← Pydantic Settings — ALL env vars live here
│   │   ├── logging.py             ← structlog setup — configure_logging(), get_logger()
│   │   ├── security.py            ← Input validation & sanitization utilities
│   │   └── utils.py               ← Pure helper functions (no I/O)
│   │
│   ├── database/
│   │   ├── connection.py          ← Motor client, DB access, index creation
│   │   ├── models/                ← Pydantic models (data shapes, to_mongo/from_mongo)
│   │   │   ├── user.py            ← User model
│   │   │   ├── chat.py            ← Chat model
│   │   │   ├── chat_settings.py   ← ChatSettings + WelcomeButton models
│   │   │   ├── join_request.py    ← JoinRequest + JoinRequestStatus + WelcomeStatus enums
│   │   │   ├── broadcast_job.py   ← BroadcastJob + BroadcastStatus + MessagePayload
│   │   │   ├── subscription.py    ← Subscription + PlanTier enum
│   │   │   └── plan.py            ← Plan model
│   │   └── repositories/          ← All DB access (Motor calls) — NEVER call Motor from handlers
│   │       ├── user_repo.py       ← UserRepository
│   │       ├── chat_repo.py       ← ChatRepository (also manages chat_admins + chat_settings)
│   │       ├── join_request_repo.py ← JoinRequestRepository
│   │       ├── broadcast_repo.py  ← BroadcastRepository (jobs + recipients)
│   │       └── subscription_repo.py ← SubscriptionRepository + Plans
│   │
│   ├── services/                  ← Business logic — orchestrates repos + Telegram API
│   │   ├── user_service.py        ← User registration, status, super admin check
│   │   ├── chat_service.py        ← Chat detection, settings, admin verification
│   │   ├── approval_service.py    ← Join request scheduling + execution + locking
│   │   ├── welcome_service.py     ← Welcome message sending + variable substitution
│   │   ├── broadcast_service.py   ← Broadcast job lifecycle (create/start/pause/resume/cancel)
│   │   ├── stats_service.py       ← Statistics aggregation (per-chat + global)
│   │   ├── subscription_service.py ← Plan checking, subscription lookup
│   │   ├── plan_service.py        ← Plan CRUD (super admin)
│   │   ├── entitlement_service.py ← Feature gate checks (can_broadcast, can_connect_chat)
│   │   ├── payment_service.py     ← Abstract PaymentProvider interface + StubPaymentProvider
│   │   ├── telegram_service.py    ← ALL Telegram API calls (never call bot directly from handlers)
│   │   └── rate_limiter.py        ← TelegramRateLimiter + UserCommandThrottler (Redis-based)
│   │
│   ├── workers/                   ← Worker classes (instantiated by workers/ entry points)
│   │   ├── approval_worker.py     ← ApprovalWorker — polls MongoDB for due approvals
│   │   └── broadcast_worker.py    ← BroadcastWorker — batch-sends broadcast jobs
│   │
│   ├── bot/
│   │   ├── handlers/              ← aiogram Routers — THIN layer, calls services only
│   │   │   ├── __init__.py        ← setup_routers() assembles all routers in correct order
│   │   │   ├── start.py           ← /start, /help, menu:main callback
│   │   │   ├── tutorial.py        ← /tutorial with 8 sections, inline navigation
│   │   │   ├── chat_member.py     ← my_chat_member updates (bot added/removed as admin)
│   │   │   ├── join_requests.py   ← chat_join_request updates (entry point for approval flow)
│   │   │   ├── chats.py           ← /mychannels, /refresh, chat:select, chat:disconnect
│   │   │   ├── settings.py        ← /settings, settings:chat: callbacks
│   │   │   ├── approval.py        ← /approval, toggle, delay, custom delay FSM
│   │   │   ├── welcome.py         ← /welcome, toggle, trigger, edit text FSM
│   │   │   ├── buttons.py         ← /buttons, button builder FSM (add/delete/preview)
│   │   │   ├── broadcast.py       ← /broadcast FSM, /broadcast_status/pause/resume/cancel
│   │   │   ├── stats.py           ← /stats, stats:chat: callbacks
│   │   │   └── superadmin.py      ← /admin /users /chats /system /plans /master_broadcast
│   │   │
│   │   ├── keyboards/             ← InlineKeyboardMarkup builder functions
│   │   │   ├── main_menu.py       ← main_menu_keyboard(), welcome_start_keyboard()
│   │   │   ├── chat_menu.py       ← chat_list_keyboard(), chat_action_keyboard()
│   │   │   ├── settings_menu.py   ← approval_settings_keyboard(), welcome_settings_keyboard()
│   │   │   ├── approval_menu.py   ← Re-exports/variants for approval UI
│   │   │   ├── welcome_menu.py    ← welcome_settings_keyboard() variants
│   │   │   ├── button_builder.py  ← button_builder_keyboard(), button_row_selector_keyboard()
│   │   │   ├── broadcast_menu.py  ← broadcast_target/confirm/control keyboards
│   │   │   └── superadmin_menu.py ← superadmin_main_keyboard(), superadmin_stats_keyboard()
│   │   │
│   │   ├── middlewares/
│   │   │   ├── database.py        ← Injects repo instances into handler data dict
│   │   │   ├── throttling.py      ← Per-user rate limiting (silently drops excess)
│   │   │   ├── auth.py            ← Injects is_super_admin bool
│   │   │   └── logging.py         ← Structured per-update logging + timing
│   │   │
│   │   └── filters/
│   │       ├── is_admin.py        ← IsChatAdmin — verifies via Telegram API
│   │       ├── is_superadmin.py   ← IsSuperAdmin — checks settings.super_admin_ids
│   │       └── callback_owner.py  ← CallbackOwner — prevents button hijacking
│   │
│   └── monitoring/
│       ├── health.py              ← aiohttp /health and /ready endpoints (port 8080)
│       └── metrics.py             ← Prometheus counters/histograms/gauges (port 9090)
│
└── tests/
    ├── conftest.py                ← Shared fixtures (AsyncMock for all repos/services/bot)
    ├── test_user_service.py
    ├── test_chat_service.py
    ├── test_approval_service.py
    ├── test_welcome_service.py
    ├── test_broadcast_service.py
    ├── test_duration_parser.py
    ├── test_auth.py
    ├── test_idempotency.py
    ├── test_rate_limiter.py
    └── load/
        ├── simulate_join_requests.py   ← 10k join request load test
        └── simulate_broadcast.py       ← 100k user broadcast load test
```

---

## 3. MONGODB COLLECTIONS — QUICK REFERENCE

| Collection | Purpose | Key Index |
|---|---|---|
| `users` | Telegram users who interacted with bot | `telegram_id` UNIQUE |
| `chats` | Groups/channels where bot is admin | `chat_id` UNIQUE |
| `chat_admins` | Many-to-many: users who manage each chat | `{chat_id, user_id}` UNIQUE |
| `chat_settings` | Per-chat configuration (approval, welcome, etc.) | `chat_id` UNIQUE |
| `join_requests` | Every join request received | `{chat_id, user_id}` partial UNIQUE (pending/scheduled) |
| `user_chat_relationships` | User-to-chat mapping for broadcast targeting | `{user_id, chat_id}` UNIQUE |
| `broadcast_jobs` | Broadcast job records | `{status, created_at}` |
| `broadcast_recipients` | Per-job, per-user delivery records | `{job_id, user_id}` UNIQUE |
| `subscriptions` | User plan subscriptions | `{user_id, status}` |
| `plans` | Plan definitions (FREE/PRO/BUSINESS/ENTERPRISE) | `plan_id` UNIQUE |
| `payment_transactions` | Payment records | `user_id`, `status` |
| `admin_actions` | Super admin audit log | TTL 90 days on `created_at` |
| `system_logs` | System event logs | TTL 30 days on `created_at` |

> All indexes created automatically on startup in `app/database/connection.py → DatabaseManager.create_indexes()`

---

## 4. DEPENDENCY INJECTION PATTERN

Services are NEVER instantiated inside handlers. Injected by middleware.

```
main.py creates services ONCE at startup:
  rate_limiter = TelegramRateLimiter(redis_client)
  telegram_service = TelegramService(bot, rate_limiter)
  user_service = UserService(UserRepository(db))
  ...

Middleware injects into handler data dict:
  DatabaseMiddleware  → user_repo, chat_repo, join_request_repo, broadcast_repo
  AuthMiddleware      → is_super_admin (bool)
  ThrottlingMiddleware → silently drops over-limit requests

Handler receives via type-hinted parameters:
  async def handler(message: Message, user_repo: UserRepository, is_super_admin: bool):
```

---

## 5. KEY BUSINESS LOGIC FLOWS

### Join Request Approval Flow
```
Telegram → chat_join_request update
  → handlers/join_requests.py (THIN — calls service only)
  → approval_service.handle_new_join_request()
      ├── Store in join_requests (idempotent via DuplicateKeyError handling)
      ├── If auto_approval_enabled AND delay=0 → approve immediately
      ├── If auto_approval_enabled AND delay>0 → set status=scheduled, scheduled_at=now+delay
      └── If welcome_trigger=on_request → welcome_service.send_welcome()

approval_worker (separate process, polls every 5s):
  → approval_service.process_due_requests(now)
      ├── MongoDB: status=scheduled AND scheduled_at<=now
      ├── Redis lock per {chat_id}:{user_id} (prevents duplicate processing)
      ├── Telegram approveChatJoinRequest
      ├── DB: status=approved
      └── welcome_service.send_welcome(trigger=on_approval)
```

### Broadcast Flow
```
/broadcast → entitlement check → FSM compose → target select → estimate → confirm
  → broadcast_service.create_broadcast_job() [DRAFT status]
  → broadcast_service.start_job() [PENDING status]

broadcast_worker (separate process, polls every 10s):
  → Gets running jobs
  → Loads recipients in batches (200 at a time via skip/limit cursor)
  → rate_limiter.acquire_global() before each send
  → On RetryAfter: sleep exact duration + jitter
  → On Forbidden: mark_recipient_failed, continue
  → Updates progress atomically ($inc processed/sent/failed)
  → On restart: resumes from pending recipients (status field)
  → When no more pending: mark job completed
```

---

## 6. CRITICAL RULES — DO NOT VIOLATE

1. **NEVER call `bot.send_*()` directly from handlers** → use `telegram_service`
2. **NEVER load all users into memory** → use `skip/limit` or MongoDB cursors
3. **NEVER create `asyncio.create_task()` per join request** → store in DB, worker picks it up
4. **NEVER broadcast from handler** → create job, let `broadcast_worker` do it
5. **ALWAYS acquire Redis lock** before executing approval (prevents duplicate welcome)
6. **ALWAYS re-verify admin** via Telegram API on sensitive actions (not just DB)
7. **ALWAYS validate callback ownership** before processing (CallbackOwner filter)
8. **NEVER retry permanent errors** (Forbidden, ChatNotFound) → log and mark failed
9. **ALWAYS handle DuplicateKeyError** in inserts → idempotent by design
10. **NEVER put secrets in source** → `.env` only, loaded via `app/core/config.py`

---

## 7. TELEGRAM API LIMITATIONS — HARD CONSTRAINTS

| Limitation | How We Handle It |
|---|---|
| Bot cannot DM users who haven't /started it | Log failure, show instructions in chat |
| Cannot enumerate all group members | Broadcast targets only our DB users |
| `can_invite_users` required to approve requests | Check on connection, warn admin immediately |
| Flood limit ~30 msg/sec global | `TelegramRateLimiter` in `rate_limiter.py` |
| Join request messaging restrictions | Catch `TelegramBadRequest`, log, continue |
| `RetryAfter` header on flood | `handle_retry_after()` sleeps exact duration |

---

## 8. ENVIRONMENT VARIABLES

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | YES | From @BotFather |
| `MONGODB_URI` | YES | MongoDB connection string |
| `MONGODB_DATABASE` | YES | e.g. `requestacceptbot` |
| `REDIS_URL` | YES | e.g. `redis://localhost:6379/0` |
| `SUPER_ADMIN_IDS` | YES | Comma-separated Telegram user IDs |
| `ENVIRONMENT` | YES | `production` or `development` |
| `WEBHOOK_URL` | Prod | Full HTTPS URL for Telegram webhook |
| `WEBHOOK_SECRET` | Prod | Secret token for webhook validation |
| `WEBHOOK_PATH` | Prod | URL path (default `/webhook`) |
| `APP_HOST` | No | Bind host (default `0.0.0.0`) |
| `APP_PORT` | No | Bot HTTP port (default `8000`) |
| `LOG_LEVEL` | No | `DEBUG`/`INFO`/`WARNING` |
| `APPROVAL_POLL_INTERVAL` | No | Worker poll seconds (default `5`) |
| `BROADCAST_BATCH_SIZE` | No | Recipients per batch (default `200`) |
| `BROADCAST_RATE_LIMIT` | No | Messages/sec for broadcast (default `25`) |

---

## 9. COMMON FIXES — WHERE TO LOOK

| Problem | Where to look |
|---|---|
| Bot doesn't detect when added as admin | `handlers/chat_member.py` → `bot_chat_member_updated()` |
| Join requests not being approved | `services/approval_service.py` + check approval_worker running |
| Approval worker not running | `workers/run_approval_worker.py` — run as separate process |
| Redis lock stuck | Key pattern: `approval_lock:{chat_id}:{user_id}` — DEL from Redis |
| Welcome messages not sending | `services/welcome_service.py` → check trigger matches settings |
| Welcome before approval fails | EXPECTED: Telegram restriction, check `join_requests.welcome_status` |
| Broadcast not starting | Check worker running + user subscription + `broadcast_jobs.status` |
| Duplicate welcome messages | `welcome_service` checks `join_request.welcome_status` before sending |
| Callback pressed by wrong user | `filters/callback_owner.py` — CallbackOwner filter |
| Settings not saved | `repositories/chat_repo.py → update_settings_field()` |
| Rate limit errors from Telegram | `services/rate_limiter.py` + check Redis is reachable |

---

## 10. FSM STATES

FSM storage: Redis via `RedisStorage` from aiogram.

| File | States Class | States |
|---|---|---|
| `handlers/approval.py` | `ApprovalStates` | `waiting_custom_delay` |
| `handlers/welcome.py` | `WelcomeStates` | `editing_text`, `waiting_custom_delay` |
| `handlers/buttons.py` | `ButtonBuilderStates` | `waiting_button_text`, `waiting_button_url`, `waiting_button_row` |
| `handlers/broadcast.py` | `BroadcastStates` | `composing_message`, `selecting_target`, `confirming` |

FSM context stores `chat_id` so handlers know which chat is being configured.

---

## 11. CALLBACK DATA NAMING CONVENTION

Format: `prefix:action:params` (max 64 bytes total)

| Prefix | Example |
|---|---|
| `menu:` | `menu:main`, `menu:chats`, `menu:settings` |
| `chat:` | `chat:select:123456`, `chat:disconnect:123456` |
| `settings:` | `settings:chat:123456` |
| `approval:` | `approval:toggle:123456`, `approval:delay:123456:900` |
| `welcome:` | `welcome:toggle:123456`, `welcome:trigger:123456:on_approval` |
| `btn:` | `btn:add:123456`, `btn:delete:123456:0`, `btn:preview:123456` |
| `broadcast:` | `broadcast:confirm:job123`, `broadcast:pause:job123` |
| `stats:` | `stats:chat:123456`, `stats:refresh:123456` |
| `tutorial:` | `tutorial:2`, `tutorial:prev:3` |
| `admin:` | `admin:users`, `admin:system` |

---

## 12. SUBSCRIPTION / PLAN ARCHITECTURE

```
plans collection → Plan (FREE, PRO, BUSINESS, ENTERPRISE) with limits
subscriptions collection → User → Plan mapping with expiry

EntitlementService.can_broadcast(user_id) → (bool, reason)
EntitlementService.can_connect_chat(user_id, count) → (bool, reason)

PaymentService uses abstract PaymentProvider interface.
StubPaymentProvider is the development placeholder.
To add real payment: implement PaymentProvider ABC in payment_service.py,
swap in main.py.
```

Default limits:
- **FREE**: 0 broadcasts, 3 connected chats
- **PRO**: 10 broadcasts/day, 1k recipients, 10 chats
- **BUSINESS**: 50/day, 10k recipients, unlimited chats
- **ENTERPRISE**: unlimited

---

## 13. LOGGING EVENTS REFERENCE

| Event | Location |
|---|---|
| `JOIN_REQUEST_RECEIVED` | `approval_service.py` |
| `JOIN_REQUEST_SCHEDULED` | `approval_service.py` |
| `JOIN_REQUEST_APPROVED` | `approval_service.py` |
| `WELCOME_SENT` | `welcome_service.py` |
| `WELCOME_FAILED` | `welcome_service.py` |
| `CHAT_CONNECTED` | `chat_service.py` |
| `CHAT_DISCONNECTED` | `chat_service.py` |
| `BROADCAST_STARTED` | `broadcast_service.py` |
| `BROADCAST_PROGRESS` | `broadcast_worker.py` |
| `BROADCAST_COMPLETED` | `broadcast_worker.py` |
| `APPROVAL_WORKER_STARTED` | `approval_worker.py` |
| `BROADCAST_WORKER_STARTED` | `broadcast_worker.py` |

Use `get_logger('module_name')` from `app/core/logging.py`. Never log secrets or tokens.

---

## 14. RUNNING THE PROJECT

```bash
# Development (long polling)
cp .env.example .env          # Set ENVIRONMENT=development
pip install -r requirements.txt
python main.py                          # Terminal 1: Bot
python workers/run_approval_worker.py   # Terminal 2: Approval worker
python workers/run_broadcast_worker.py  # Terminal 3: Broadcast worker

# Production (Docker)
cp .env.example .env          # Set ENVIRONMENT=production + WEBHOOK_URL + WEBHOOK_SECRET
docker-compose up -d

# Tests
pytest tests/ -v --tb=short
pytest tests/test_approval_service.py -v
pytest tests/ -k "idempotency" -v

# Load tests
python tests/load/simulate_join_requests.py --requests 10000
python tests/load/simulate_broadcast.py --users 100000
```

---

## 15. ENDPOINTS

| Endpoint | Port | Description |
|---|---|---|
| `POST /webhook` | 8000 | Telegram webhook (production) |
| `GET /health` | 8080 | App alive check |
| `GET /ready` | 8080 | MongoDB + Redis connectivity check |
| `GET /metrics` | 9090 | Prometheus metrics |

---

## 16. AGENT CHANGE GUIDE

| Task | What to change |
|---|---|
| Add a new command | Handler in `bot/handlers/`, register in `bot/handlers/__init__.py` |
| Add a new setting | `models/chat_settings.py` → `repositories/chat_repo.py` → keyboard + handler |
| Add a new collection | `models/` → `repositories/` → indexes in `database/connection.py` |
| Add payment provider | Implement `PaymentProvider` ABC in `services/payment_service.py` |
| Change broadcast logic | Only `services/broadcast_service.py` + `workers/broadcast_worker.py` |
| Debug a user | Query `users` by `telegram_id`, then `join_requests` by `user_id` |
| Debug a chat | Query `chats` + `chat_settings` by `chat_id` |
| Debug a broadcast | Query `broadcast_jobs` by `job_id`, then `broadcast_recipients` by `job_id` |
