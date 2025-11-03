# Database Schema

This file contains the SQL schema for reference. To apply migrations, use Supabase Dashboard or run SQL directly.

## Tables

### users
```sql
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_user_id INTEGER UNIQUE NOT NULL,
    username VARCHAR,
    first_name VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_telegram_user_id ON users(telegram_user_id);
```

### chats
```sql
CREATE TABLE IF NOT EXISTS chats (
    id SERIAL PRIMARY KEY,
    telegram_chat_id INTEGER UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    chat_type VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_chats_telegram_chat_id ON chats(telegram_chat_id);
CREATE INDEX IF NOT EXISTS idx_chat_user_id ON chats(user_id);
```

### messages
```sql
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER NOT NULL REFERENCES chats(id),
    telegram_message_id INTEGER NOT NULL,
    text TEXT,
    from_user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_message_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_message_from_user_id ON messages(from_user_id);
```

### spreadsheet_configs
```sql
CREATE TABLE IF NOT EXISTS spreadsheet_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
    spreadsheet_id VARCHAR,
    oauth_token TEXT,
    refresh_token TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_spreadsheet_configs_user_id ON spreadsheet_configs(user_id);
```

## How to Apply Migrations

1. **Via Supabase Dashboard**: Go to SQL Editor and run the SQL
2. **Via Supabase CLI**: `supabase db push`
3. **Via psql**: Connect directly and run SQL

## Notes

- All timestamps use `TIMESTAMP WITH TIME ZONE` for proper timezone handling
- Foreign keys ensure referential integrity
- Indexes improve query performance

