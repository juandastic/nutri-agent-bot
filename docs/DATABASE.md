# Database Architecture

## Overview
This application uses **Supabase SDK** for all database operations. No ORM or migration tools are used.

## Architecture

### Application Code
- **Supabase SDK** (`app/db/supabase_client.py`): Handles all database operations via REST API
- **Database Utils** (`app/db/utils.py`): Functions using Supabase SDK
- **No SQLAlchemy, No Alembic**: Completely removed for simplicity

### Database Schema
- **SQL Schema** (`database/schema.sql`): Reference SQL schema
- **Migrations**: Apply directly via Supabase Dashboard or SQL

## Why This Architecture?

1. **Supabase SDK**: Avoids pgbouncer prepared statement issues
2. **Simplicity**: No ORM, no migration tools, no complex abstractions
3. **Direct Control**: SQL schema is clear and straightforward

## Files Structure

```
app/db/
├── supabase_client.py  # Supabase client (used by app)
└── utils.py           # Database functions (uses Supabase SDK)

database/
└── schema.sql         # SQL schema reference
```

## Migration Workflow

1. Update `database/schema.sql` with your changes
2. Apply via Supabase Dashboard SQL Editor or CLI
3. Done!

## Important Notes

- All database operations use Supabase SDK
- Schema changes are applied directly via SQL
- No migration tracking - keep schema.sql updated

