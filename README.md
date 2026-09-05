# RequestAcceptBot

A production-grade Telegram bot for automatically handling join requests, managing community welcome messages, and broadcasting to users. Built with modern async Python, aiogram 3.x, MongoDB, and Redis.

## Features

- **Auto-Approval**: Automatically approve join requests for channels and supergroups.
- **Delayed Approvals**: Optionally add a delay before approving users.
- **Welcome Messages**: Send customizable welcome messages (with variables and inline buttons) upon approval.
- **Broadcast System**: Send messages to users across all managed chats with advanced rate limiting and deduplication.
- **Subscription Entitlements**: Support for FREE and PRO tiers, controlling broadcast reach and feature access.
- **High Performance**: Asynchronous architecture designed to handle thousands of requests seamlessly without blocking.
- **Idempotency & Resiliency**: Built-in mechanisms to prevent duplicate actions and graceful handling of Telegram API rate limits.

## Architecture

```text
+-------------------+      Webhooks      +-------------------+
|                   | -----------------> |                   |
|   Telegram API    |                    |  RequestAcceptBot |
|                   | <----------------- |    (aiogram 3)    |
+-------------------+      API Calls     +-------------------+
                                           |       |
                                           |       |
                      +------------------+ |       | +------------------+
                      |                  | |       | |                  |
                      |   Redis (Cache/  |-+       +-| MongoDB (Data &  |
                      |   Locks/Jobs)    |           | Source of Truth) |
                      +------------------+           +------------------+
```

## Requirements

- Python 3.12+
- MongoDB 7.0+
- Redis 7.0+
- Telegram Bot Token from [@BotFather](https://t.me/botfather)

## Quick Start (Local Development)

```bash
git clone https://github.com/yourusername/RequestAcceptBot.git
cd RequestAcceptBot
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your specific values (BOT_TOKEN, MONGODB_URI, etc.)
python main.py
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Your Telegram Bot Token | (Required) |
| `MONGODB_URI` | MongoDB Connection String | `mongodb://localhost:27017` |
| `MONGODB_DB_NAME` | MongoDB Database Name | `request_accept_bot` |
| `REDIS_URL` | Redis Connection URL | `redis://localhost:6379/0` |
| `SUPER_ADMIN_IDS` | Comma-separated list of Telegram User IDs | (Required) |
| `WEBHOOK_URL` | URL for Telegram Webhook | (Optional, uses polling if empty) |

## Telegram Setup

### Creating the Bot
1. Open [@BotFather](https://t.me/botfather) in Telegram.
2. Send `/newbot` and follow the prompts.
3. Copy the API token provided.

### Required Bot Permissions
When adding the bot as admin to a channel or group, these permissions are required:
- ✅ **Invite Users via Link** (`can_invite_users`) — Required to approve join requests.
- ⬜ Add Admins — Optional, for admin change notifications.

### Enabling Join Requests
1. Go to your Group/Channel settings.
2. Navigate to Edit → Invite Links.
3. Create a new link and enable "Approve New Members".

## MongoDB Setup
- Use a standard connection string: `mongodb://user:pass@host:port/`
- Indexes are created automatically on startup by the repository layers.
- For production, using MongoDB Atlas is highly recommended.

## Redis Setup
- Use a standard connection URL: `redis://:password@host:port/db`
- Used for distributed locks (approval deduplication) and caching.

## Docker Deployment

```bash
cp .env.example .env
# Edit .env to match your setup
docker-compose up -d
```
*Note: In production, it is recommended to use managed MongoDB (e.g., Atlas) and managed Redis (e.g., Upstash, Redis Cloud) instead of local Docker services.*

## Webhook Deployment

For production, webhooks are recommended over polling:
1. Ensure your server has a public IP/Domain and an SSL certificate (e.g., via Let's Encrypt).
2. Set up an Nginx reverse proxy to forward requests to the bot's internal port.
3. Set the `WEBHOOK_URL` environment variable.

## Scaling

- **Horizontal Bot Scaling**: You can deploy multiple webhook receivers behind a load balancer.
- **Worker Scaling**: Background tasks (broadcasts, delayed approvals) can be handled by dedicated worker processes.
- **Database**: Configure MongoDB connection pooling suitably and consider Redis clustering for heavy load.

## Commands Reference

| Command | Description | Access |
|---------|-------------|--------|
| `/start` | Start the bot and view main menu | All Users |
| `/settings` | Configure chat auto-approval & welcomes | Chat Admins |
| `/broadcast` | Create and manage broadcast jobs | Pro / Admins |
| `/stats` | View global bot usage statistics | Super Admins |

## Broadcast System

- **How it works**: Uses an asynchronous worker to stream recipients from MongoDB, reducing memory footprint.
- **Media Support**: Supports text, photos, and standard inline keyboards.
- **Rate Limiting**: Strictly adheres to Telegram's 30 msgs/sec global limit to prevent bans.
- **Deduplication**: Ensures a user only receives one broadcast message, even if they are in multiple groups managed by the bot.
- **Control**: Jobs can be paused, resumed, or cancelled at any time.

## Subscription Plans

- **FREE Plan**: Basic auto-approval, limited delayed approval options, no broadcast features.
- **PRO Plan**: Unlimited broadcasts, custom welcome variables, advanced analytics.
- *(Payment integration module is a placeholder and should be implemented as per business needs).*

## Troubleshooting

- **Bot not approving requests**: Ensure the bot is an admin with the "Invite Users" permission.
- **Redis Connection Errors**: Check your network settings and password in the `.env` file.
- **Rate Limit Bans**: Ensure background tasks are not circumventing the `RateLimiter` component.

## Known Telegram Limitations

1. The bot cannot initiate a conversation with users who haven't started it (sent `/start`).
2. The bot cannot enumerate all members of a group due to API limitations.
3. Join request messaging and welcomes are subject to strict Telegram spam algorithms.
4. General API flood limits apply across the bot token.
5. The bot *must* have `can_invite_users` permission to approve join requests.

## License

MIT License. See `LICENSE` for details.
