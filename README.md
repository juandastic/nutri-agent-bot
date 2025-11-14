# NutriAgent Bot

A conversational Telegram bot that helps you track your nutrition and meals through natural language conversations and image recognition. Send photos of your meals or describe them in text, and the bot will intelligently detect ingredients and estimate nutritional information. Connect your Google account to automatically record all your nutrition data in your own Google Sheets spreadsheet.

## 🎯 Project Goal

NutriAgent Bot makes nutrition tracking effortless by combining the convenience of Telegram messaging with the power of AI and your own data storage. Instead of manually logging meals in apps, simply chat with the bot about what you ate (or send a photo), and it will intelligently extract and record the information in a spreadsheet you own and control.

## 💡 The Idea

Nutrition tracking shouldn't be complicated or require switching between multiple apps. NutriAgent Bot provides a seamless experience:

1. **Talk Naturally**: Chat with the bot directly in Telegram about your meals, snacks, and nutrition goals using natural language or send photos
2. **AI-Powered Understanding**: The bot uses AI to understand what you ate from text or images, extract nutritional information, and ask clarifying questions when needed. You can refine estimations by adding context - for example, sending a photo of french fries with a caption explaining they were air-fried instead of deep-fried
3. **Your Data, Your Control**: Connect your Google account once, and the bot creates a new spreadsheet in your Google Drive to store all your nutrition data
4. **Own Your Spreadsheet**: Unlike other nutrition apps, your data lives in a Google Sheet you own and can access, edit, or extend anytime

### How It Works

- Start a conversation with the bot on Telegram
- Share what you ate in two ways:
  - **Text messages**: "I had a grilled chicken salad with olive oil dressing for lunch"
  - **Images**: Send a photo of your meal and the bot will detect ingredients and estimate nutritional information
  - **Refine estimations conversationally**: Add context to improve accuracy. For example, take a picture of french fries but add a caption like "these weren't fried in oil, they were prepared in an air fryer" - the bot will adjust the nutritional estimation accordingly
- When you're ready to start tracking, connect your Google account
- The bot creates a new Google Sheet and begins recording your meals automatically
- All your nutrition data is stored in your spreadsheet, which you can view, edit, or analyze however you want

## ✨ Features

- **Natural Language Processing**: Chat with the bot about your meals using everyday language
- **Image Recognition**: Send photos of your meals and the bot will detect ingredients and estimate nutritional information
- **Conversational Refinement**: Improve accuracy by adding context through conversation. For example, send a photo of french fries with a caption explaining they were air-fried instead of deep-fried, and the bot will adjust its nutritional estimation accordingly
- **Intelligent Meal Extraction**: AI-powered agent extracts nutrition information from both text messages and images
- **Google Sheets Integration**: Automatically creates and updates a spreadsheet in your Google Drive
- **OAuth Authentication**: Secure Google account connection using OAuth 2.0
- **Conversational Interface**: Ask questions, get clarifications, and manage your nutrition goals through conversation
- **Data Ownership**: All your data is stored in your own Google Sheet - you have full control and access
- **Telegram Integration**: Access your nutrition tracker directly from Telegram, no separate app needed

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- A Telegram Bot Token (obtain from [@BotFather](https://t.me/BotFather))
- A Google Cloud Project with OAuth 2.0 credentials (for Google Sheets integration)
- A Supabase project (for data storage)
- An OpenAI API key (for AI-powered meal understanding)
- A publicly accessible HTTPS URL for webhook (or use ngrok/local tunnel for development)

### Installation

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
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_api_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
WEBHOOK_URL=https://yourdomain.com/webhook
```





### Running the Application

#### Development

Run the application with uvicorn:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the entry point:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

#### Production

For production, use a process manager like systemd or supervisor. Example with uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 🔧 Development Setup

### Development with ngrok

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

6. Send a message to your bot on Telegram - it should respond!

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

2. **When restarting ngrok:**
   - ngrok URLs change each time you restart (unless you have a paid plan with a fixed domain)
   - Just call `/setup-webhook` using the new ngrok URL:
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

## 📡 API Endpoints

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
Receives Telegram updates. This endpoint is called by Telegram when messages are sent to your bot. Processes messages with AI and handles meal tracking.

**Note:** This endpoint should be publicly accessible via HTTPS. Telegram will send POST requests to this endpoint with update JSON payloads.

### `POST /api/answer`
Process a conversation turn coming from an external frontend (web/mobile) using multipart/form-data. Accepts text, optional images, and user metadata to interact with the NutriAgent.

**Fields:**
- `external_user_id` (required, form field): External user identifier.
- `username` (optional, form field): Username or email to associate with the user.
- `name` (optional, form field): Human readable name for the user.
- `external_chat_id` (optional, form field): Chat identifier. When omitted, a general chat per user is used.
- `message_text` (optional, form field): Message text for the agent.
- `images` (optional, file field, repeatable): One or more image files to analyze.

### `GET /api/messages`
Retrieve the recent conversation history for an external user. Returns the latest messages associated with the resolved chat.

**Query parameters:**
- `external_user_id` (required): External user identifier.
- `external_chat_id` (optional): Explicit chat identifier. When omitted, the default per-user chat is used.
- `limit` (optional, default 20, max 100): Number of recent messages to return.

## ⚙️ Environment Variables

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
Enable observability and tracing with LangSmith for agent tracking:

- `LANGSMITH_API_KEY`: Your LangSmith API key (optional, for tracing)
- `LANGSMITH_TRACING`: Set to "true" to enable tracing (default: "false")
- `LANGSMITH_PROJECT`: Project name in LangSmith (default: "nutri-agent-bot")
- `LANGSMITH_ENDPOINT`: LangSmith API endpoint URL (optional, defaults to LangSmith's public endpoint)

**To enable LangSmith tracing:**
1. Get your API key from [LangSmith](https://smith.langchain.com/)
2. Add to your `.env` file:
   ```
   LANGSMITH_API_KEY=your_api_key_here
   LANGSMITH_TRACING=true
   LANGSMITH_PROJECT=nutri-agent-bot
   LANGSMITH_ENDPOINT=https://api.smith.langchain.com  # Optional, only if using custom endpoint
   ```

When enabled, all agent executions will be automatically traced and visible in your LangSmith dashboard.

## 📝 Code Formatting

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

## 📁 Project Structure

```
nutriAgentBot/
├── main.py                      # Entry point for running the application
├── requirements.txt             # Python dependencies
├── pyproject.toml               # Ruff configuration for code formatting
├── format.sh                    # Script for formatting code
├── .env.example                 # Example environment variables file
├── README.md                    # This file
├── database/                    # Database schema files
│   └── schema.sql               # Database schema definitions
├── docs/                        # Documentation
│   └── DATABASE.md              # Database documentation
├── logs/                        # Application logs
│   ├── app.log                  # Application logs
│   └── errors.log               # Error logs
└── app/                         # Main application package
    ├── __init__.py
    ├── main.py                  # FastAPI application initialization
    ├── config.py                # Configuration and settings
    ├── routers/                 # API route handlers
    │   ├── __init__.py
    │   ├── webhook.py           # Webhook endpoints
    │   └── auth.py              # OAuth authentication endpoints
    ├── services/                # Business logic services
    │   ├── __init__.py
    │   ├── telegram_service.py  # Telegram API interactions
    │   ├── message_handler.py   # Message processing logic
    │   ├── google_sheets_service.py  # Google Sheets integration
    │   └── google_oauth_service.py   # Google OAuth flow
    ├── agents/                  # LangChain agents
    │   ├── __init__.py
    │   └── langchain_agent.py   # LangChain agent for message processing
    ├── tools/                   # LangChain tools
    │   ├── __init__.py
    │   └── spreadsheet_tool.py  # Tool for spreadsheet operations
    ├── db/                      # Database utilities
    │   ├── supabase_client.py   # Supabase client configuration
    │   └── utils.py             # Database helper functions
    ├── models/                  # Pydantic models and schemas
    │   ├── __init__.py
    │   └── schemas.py           # API request/response models
    ├── prompts/                 # Prompt templates
    │   └── food_analysis_prompt.txt  # Food analysis prompt template
    ├── templates/               # HTML templates
    │   └── auth_success.html    # OAuth success page template
    └── utils/                   # Utility functions
        ├── __init__.py
        └── logging.py           # Logging configuration
```

## 🛠️ Error Handling

The application includes proper error handling:
- Validates environment variables are set
- Handles Telegram API errors gracefully
- Returns appropriate HTTP status codes
- Logs errors for debugging

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
