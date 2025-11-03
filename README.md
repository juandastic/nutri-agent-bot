# Telegram Bot Webhook FastAPI Application

A FastAPI application for managing a Telegram bot using webhooks. This application provides endpoints to setup and delete webhooks, and handles incoming Telegram messages.

## Features

- **Setup Webhook**: Configure Telegram bot to receive updates via webhook
- **Delete Webhook**: Remove webhook configuration from Telegram bot
- **Message Handler**: Receive and process Telegram messages, responding with "Hello World"

## Prerequisites

- Python 3.8 or higher
- A Telegram Bot Token (obtain from [@BotFather](https://t.me/BotFather))
- A publicly accessible HTTPS URL for webhook (or use ngrok/local tunnel for development)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd nutriAgentBot
```

2. Create and activate a virtual environment (recommended):

**On macOS/Linux:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

**On Windows:**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate
```

You'll know it's activated when you see `(venv)` at the start of your terminal prompt.

3. Install dependencies:
```bash
pip install -r requirements.txt
```

**Note:** If you get a "command not found" error, try `pip3` instead of `pip`.

4. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` and add your values:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
WEBHOOK_URL=https://yourdomain.com/webhook
```

## Using Virtual Environments

### What is a virtual environment?

A virtual environment is an isolated Python environment that keeps your project dependencies separate from your system Python. This prevents conflicts between different projects and is considered a best practice.

### Daily Usage

**Activate the virtual environment** (do this every time you open a new terminal to work on the project):
```bash
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows
```

**Deactivate** when you're done:
```bash
deactivate
```

**Important:** Always activate the virtual environment before:
- Installing packages (`pip install`)
- Running the application
- Running any Python scripts

### Troubleshooting

- If `python3 -m venv venv` doesn't work, make sure Python 3 is installed: `python3 --version`
- If you see "command not found" for `pip`, try `pip3` instead
- The `venv` folder is already in `.gitignore`, so it won't be committed to git

## Running the Application

### Development

Run the application with uvicorn:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the entry point:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

### Production

For production, use a process manager like systemd or supervisor. Example with uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### `GET /`
Health check endpoint. Returns a simple status message.

### `POST /setup-webhook`
Sets up the Telegram webhook. The webhook URL is automatically detected from the request headers.

**Usage:**
Call this endpoint using your public URL (e.g., ngrok URL), and it will automatically set the webhook to `{scheme}://{host}/webhook`

**Example:**
```bash
# Call via ngrok HTTPS URL
curl -X POST https://your-ngrok-url.ngrok.io/setup-webhook
# Webhook will be automatically set to: https://your-ngrok-url.ngrok.io/webhook
```

**Response:**
```json
{
  "success": true,
  "message": "Webhook set successfully",
  "webhook_url": "https://your-ngrok-url.ngrok.io/webhook",
  "telegram_response": {
    "ok": true,
    "result": true,
    "description": "Webhook was set"
  }
}
```

### `POST /delete-webhook`
Deletes the Telegram webhook. Reads `TELEGRAM_BOT_TOKEN` from environment variable.

**Example:**
```bash
curl -X POST http://localhost:8000/delete-webhook
```

**Response:**
```json
{
  "success": true,
  "message": "Webhook deleted successfully",
  "telegram_response": {
    "ok": true,
    "result": true,
    "description": "Webhook was deleted"
  }
}
```

### `POST /webhook`
Receives Telegram updates. This endpoint is called by Telegram when messages are sent to your bot. Responds with "Hello World" to text messages.

**Note:** This endpoint should be publicly accessible via HTTPS. Telegram will send POST requests to this endpoint with update JSON payloads.

## Development with ngrok

For local development, you can use [ngrok](https://ngrok.com/) to expose your local server:

1. Install ngrok
2. Start your FastAPI application:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. In another terminal, start ngrok:
```bash
ngrok http 8000
```

4. Copy the HTTPS URL from ngrok (e.g., `https://abc123.ngrok.io`)

5. Call the setup endpoint using the ngrok URL (it will auto-detect):
```bash
curl -X POST https://abc123.ngrok.io/setup-webhook
```

**Note:** The endpoint automatically detects the URL from the request - no need to configure anything!

6. Send a message to your bot on Telegram - it should respond with "Hello World"!

### Important: What Happens When ngrok Stops?

**When you stop ngrok:**
- The ngrok URL becomes invalid immediately
- Telegram will try to send updates to your bot but the webhook URL will fail
- Telegram will retry sending updates for a period of time (usually a few hours)
- After repeated failures, Telegram will stop trying and your bot will stop receiving messages
- **Messages sent during this time may be lost**

**Best Practices:**

1. **Always delete the webhook before stopping ngrok (recommended):**
   ```bash
   curl -X POST http://localhost:8000/delete-webhook
   ```
   This tells Telegram to stop sending updates, preventing failed delivery attempts.

2. **When restarting ngrok (simplified!):**
   - ngrok URLs change each time you restart (unless you have a paid plan with a fixed domain)
   - **No need to update `.env` anymore!** Just call `/setup-webhook` using the new ngrok URL:
     ```bash
     curl -X POST https://new-ngrok-url.ngrok.io/setup-webhook
     ```
   - The endpoint will auto-detect the URL from the request and use it
   - **Note:** Calling `/setup-webhook` again will automatically replace the old webhook URL with the new one, so you don't strictly need to delete first - but it's cleaner to do so

3. **What if you forget to delete?**
   - If you restart ngrok and call `/setup-webhook` again without deleting, it will still work
   - The new `/setup-webhook` call replaces the old (dead) URL with the new one
   - Telegram will simply start using the new URL immediately
   - You might see some failed delivery attempts in Telegram's logs for the brief period between old URL dying and new URL being set

4. **For production:** Use a permanent server with a fixed HTTPS URL instead of ngrok

5. **Alternative for development:** Consider using Telegram's polling mode instead of webhooks for local development (this requires modifying the code to use `getUpdates` instead of webhooks)

## Environment Variables

### Required
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token (required)
- `SUPABASE_URL`: Your Supabase project URL (required)
- `SUPABASE_KEY`: Your Supabase API key (required)
- `OPENAI_API_KEY`: Your OpenAI API key (required)

### Optional
- `WEBHOOK_URL`: Your webhook URL (optional, auto-detected if not set)
- `GOOGLE_CLIENT_ID`: Google OAuth client ID (optional, required for Google Sheets integration)
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret (optional, required for Google Sheets integration)
- `LOG_LEVEL`: Logging level (default: "INFO")
- `ENVIRONMENT`: Environment name (default: "development")

### LangSmith Tracing (Optional)
Enable observability and tracing with LangSmith:

- `LANGSMITH_API_KEY`: Your LangSmith API key (optional, for tracing)
- `LANGSMITH_TRACING`: Set to "true" to enable tracing (default: "false")
- `LANGSMITH_PROJECT`: Project name in LangSmith (default: "nutri-agent-bot")

**To enable LangSmith tracing:**
1. Get your API key from [LangSmith](https://smith.langchain.com/)
2. Add to your `.env` file:
   ```
   LANGSMITH_API_KEY=your_api_key_here
   LANGSMITH_TRACING=true
   LANGSMITH_PROJECT=nutri-agent-bot
   ```

When enabled, all agent executions will be automatically traced and visible in your LangSmith dashboard.

## Code Formatting

This project uses [ruff](https://docs.astral.sh/ruff/) for code formatting and linting to ensure consistent code style and remove trailing spaces.

### Setup (in your virtual environment)

1. Make sure your venv is activated:
```bash
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows
```

2. Install ruff:
```bash
pip install ruff
```

### Usage

**Format all Python files:**
```bash
ruff format .
```

**Check and auto-fix linting issues:**
```bash
ruff check --fix .
```

**Format and lint in one command:**
```bash
ruff format . && ruff check --fix .
```

Or use the provided script:
```bash
./format.sh
```

### Configuration

- Formatting rules are configured in `pyproject.toml`
- Maximum line length: 100 characters
- Uses double quotes for strings
- Automatically removes trailing whitespace

## Project Structure

```
nutriAgentBot/
├── main.py                      # Entry point for running the application
├── requirements.txt             # Python dependencies
├── .env.example                 # Example environment variables file
├── README.md                    # This file
└── app/                         # Main application package
    ├── __init__.py
    ├── main.py                  # FastAPI application initialization
    ├── config.py                # Configuration and settings
    ├── routers/                 # API route handlers
    │   ├── __init__.py
    │   └── webhook.py           # Webhook endpoints
    ├── services/                # Business logic services
    │   ├── __init__.py
    │   ├── telegram_service.py  # Telegram API interactions
    │   └── message_handler.py  # Message processing logic
    ├── agents/                  # LangChain agents (for future features)
    │   ├── __init__.py
    │   └── langchain_agent.py   # LangChain agent for message processing
    ├── commands/                # Custom command handlers (for future features)
    │   ├── __init__.py
    │   └── setup_commands.py    # Setup commands (Google OAuth, etc.)
    ├── models/                  # Pydantic models and schemas
    │   ├── __init__.py
    │   └── schemas.py           # API request/response models
    └── utils/                   # Utility functions
        └── __init__.py
```

### Future Features

The project structure is designed to accommodate future features:

- **LangChain Integration**: The `app/agents/` folder contains placeholder code for integrating LangChain agents to process messages with images and attachments
- **Custom Commands**: The `app/commands/` folder is ready for custom setup commands like Google OAuth and spreadsheet connections
- **Scalable Architecture**: The separation of routers, services, and models allows for easy extension and maintenance

## Error Handling

The application includes proper error handling:
- Validates environment variables are set
- Handles Telegram API errors gracefully
- Returns appropriate HTTP status codes
- Logs errors for debugging

## License

[Add your license here]
