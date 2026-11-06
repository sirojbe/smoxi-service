"""SQLite schema compatibility patches for evolving models."""

from __future__ import annotations

from sqlalchemy import Engine, inspect, text


def apply_sqlite_schema_patches(engine: Engine) -> None:
    """
    Add missing columns for existing SQLite databases.

    ``create_all`` does not alter existing tables; this keeps desktop installs
    upgradeable without a full migration run during early MVP.
    """
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        if "work_orders" in tables:
            columns = {col["name"] for col in inspector.get_columns("work_orders")}
            if "technician_id" not in columns:
                connection.execute(
                    text("ALTER TABLE work_orders ADD COLUMN technician_id INTEGER")
                )
            if "work_scope" not in columns:
                connection.execute(text("ALTER TABLE work_orders ADD COLUMN work_scope TEXT"))
            if "parts_cost_total" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE work_orders ADD COLUMN parts_cost_total INTEGER "
                        "NOT NULL DEFAULT 0"
                    )
                )
            if "parts_sale_total" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE work_orders ADD COLUMN parts_sale_total INTEGER "
                        "NOT NULL DEFAULT 0"
                    )
                )
            if "expense_total" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE work_orders ADD COLUMN expense_total INTEGER "
                        "NOT NULL DEFAULT 0"
                    )
                )
            if "public_token" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE work_orders ADD COLUMN public_token VARCHAR(64)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS "
                        "ix_work_orders_public_token ON work_orders (public_token)"
                    )
                )
            if "branch_id" not in columns:
                connection.execute(
                    text("ALTER TABLE work_orders ADD COLUMN branch_id INTEGER")
                )
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_work_orders_branch_id "
                        "ON work_orders (branch_id)"
                    )
                )
        if "work_order_parts" in tables:
            part_cols = {col["name"] for col in inspector.get_columns("work_order_parts")}
            if "inventory_item_id" not in part_cols:
                connection.execute(
                    text(
                        "ALTER TABLE work_order_parts ADD COLUMN inventory_item_id INTEGER"
                    )
                )
        if "customers" in tables:
            columns = {col["name"] for col in inspector.get_columns("customers")}
            if "telegram_chat_id" not in columns:
                connection.execute(
                    text("ALTER TABLE customers ADD COLUMN telegram_chat_id VARCHAR(64)")
                )
            if "business_client_id" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE customers ADD COLUMN business_client_id INTEGER"
                    )
                )
        if "companies" in tables:
            columns = {col["name"] for col in inspector.get_columns("companies")}
            if "telegram_bot_token" not in columns:
                connection.execute(
                    text("ALTER TABLE companies ADD COLUMN telegram_bot_token VARCHAR(512)")
                )
            if "telegram_bot_username" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE companies ADD COLUMN telegram_bot_username VARCHAR(64)"
                    )
                )
            if "telegram_staff_pin" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE companies ADD COLUMN telegram_staff_pin VARCHAR(16)"
                    )
                )
            if "telegram_staff_chat_ids" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE companies ADD COLUMN "
                        "telegram_staff_chat_ids VARCHAR(512)"
                    )
                )
            if "telegram_mini_app_url" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE companies ADD COLUMN "
                        "telegram_mini_app_url VARCHAR(512)"
                    )
                )
            if "cloudflare_tunnel_token" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE companies ADD COLUMN "
                        "cloudflare_tunnel_token VARCHAR(1024)"
                    )
                )
        if "users" in tables:
            user_cols = {col["name"] for col in inspector.get_columns("users")}
            if "telegram_chat_id" not in user_cols:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN telegram_chat_id VARCHAR(64)")
                )
        if "telegram_messages" not in tables:
            connection.execute(
                text(
                    """
                    CREATE TABLE telegram_messages (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        uuid VARCHAR(36) NOT NULL UNIQUE,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        created_by INTEGER,
                        updated_by INTEGER,
                        deleted_at DATETIME,
                        version INTEGER NOT NULL DEFAULT 1,
                        sync_status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        company_id INTEGER NOT NULL,
                        customer_id INTEGER,
                        work_order_id INTEGER,
                        chat_id VARCHAR(64) NOT NULL,
                        direction VARCHAR(16) NOT NULL,
                        body TEXT NOT NULL,
                        telegram_message_id INTEGER,
                        is_read BOOLEAN NOT NULL DEFAULT 0,
                        is_auto BOOLEAN NOT NULL DEFAULT 0,
                        FOREIGN KEY(company_id) REFERENCES companies (id),
                        FOREIGN KEY(customer_id) REFERENCES customers (id),
                        FOREIGN KEY(work_order_id) REFERENCES work_orders (id)
                    )
                    """
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_telegram_messages_company_id "
                    "ON telegram_messages (company_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_telegram_messages_chat_id "
                    "ON telegram_messages (chat_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_telegram_messages_customer_id "
                    "ON telegram_messages (customer_id)"
                )
            )
        if "app_notifications" not in tables:
            connection.execute(
                text(
                    """
                    CREATE TABLE app_notifications (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        uuid VARCHAR(36) NOT NULL UNIQUE,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        created_by INTEGER,
                        updated_by INTEGER,
                        deleted_at DATETIME,
                        version INTEGER NOT NULL DEFAULT 1,
                        sync_status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        company_id INTEGER NOT NULL,
                        title VARCHAR(200) NOT NULL,
                        body TEXT NOT NULL,
                        kind VARCHAR(40) NOT NULL DEFAULT 'info',
                        route VARCHAR(64),
                        ref_key VARCHAR(128),
                        customer_id INTEGER,
                        is_read BOOLEAN NOT NULL DEFAULT 0,
                        FOREIGN KEY(company_id) REFERENCES companies (id),
                        FOREIGN KEY(customer_id) REFERENCES customers (id)
                    )
                    """
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_app_notifications_company_id "
                    "ON app_notifications (company_id)"
                )
            )
        if "work_order_timeline_events" not in tables:
            connection.execute(
                text(
                    """
                    CREATE TABLE work_order_timeline_events (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        uuid VARCHAR(36) NOT NULL UNIQUE,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        created_by INTEGER,
                        updated_by INTEGER,
                        deleted_at DATETIME,
                        version INTEGER NOT NULL DEFAULT 1,
                        sync_status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        company_id INTEGER NOT NULL,
                        work_order_id INTEGER NOT NULL,
                        event_code VARCHAR(64) NOT NULL,
                        visibility VARCHAR(16) NOT NULL DEFAULT 'staff',
                        title VARCHAR(200) NOT NULL,
                        notes TEXT,
                        from_status VARCHAR(40),
                        to_status VARCHAR(40),
                        actor_id INTEGER,
                        FOREIGN KEY(company_id) REFERENCES companies (id),
                        FOREIGN KEY(work_order_id) REFERENCES work_orders (id)
                    )
                    """
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_timeline_work_order_id "
                    "ON work_order_timeline_events (work_order_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_timeline_company_id "
                    "ON work_order_timeline_events (company_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_timeline_event_code "
                    "ON work_order_timeline_events (event_code)"
                )
            )
        if "calendar_events" not in tables:
            connection.execute(
                text(
                    """
                    CREATE TABLE calendar_events (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        uuid VARCHAR(36) NOT NULL UNIQUE,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        created_by INTEGER,
                        updated_by INTEGER,
                        deleted_at DATETIME,
                        version INTEGER NOT NULL DEFAULT 1,
                        sync_status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        company_id INTEGER NOT NULL,
                        title VARCHAR(200) NOT NULL,
                        description TEXT,
                        event_type VARCHAR(32) NOT NULL DEFAULT 'appointment',
                        starts_at DATETIME NOT NULL,
                        ends_at DATETIME NOT NULL,
                        all_day BOOLEAN NOT NULL DEFAULT 0,
                        work_order_id INTEGER,
                        technician_id INTEGER,
                        location VARCHAR(200),
                        color VARCHAR(16),
                        reminder_minutes INTEGER,
                        FOREIGN KEY(company_id) REFERENCES companies (id),
                        FOREIGN KEY(work_order_id) REFERENCES work_orders (id),
                        FOREIGN KEY(technician_id) REFERENCES technicians (id)
                    )
                    """
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_calendar_events_company_id "
                    "ON calendar_events (company_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_calendar_events_starts_at "
                    "ON calendar_events (starts_at)"
                )
            )
        if "automation_rules" not in tables:
            connection.execute(
                text(
                    """
                    CREATE TABLE automation_rules (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        uuid VARCHAR(36) NOT NULL UNIQUE,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        created_by INTEGER,
                        updated_by INTEGER,
                        deleted_at DATETIME,
                        version INTEGER NOT NULL DEFAULT 1,
                        sync_status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        company_id INTEGER NOT NULL,
                        name VARCHAR(150) NOT NULL,
                        description TEXT,
                        trigger_type VARCHAR(40) NOT NULL,
                        trigger_value VARCHAR(120),
                        action_type VARCHAR(40) NOT NULL,
                        action_payload TEXT,
                        is_enabled BOOLEAN NOT NULL DEFAULT 1,
                        last_run_at DATETIME,
                        run_count INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY(company_id) REFERENCES companies (id)
                    )
                    """
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_automation_rules_company_id "
                    "ON automation_rules (company_id)"
                )
            )
        if "automation_runs" not in tables:
            connection.execute(
                text(
                    """
                    CREATE TABLE automation_runs (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        uuid VARCHAR(36) NOT NULL UNIQUE,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        created_by INTEGER,
                        updated_by INTEGER,
                        deleted_at DATETIME,
                        version INTEGER NOT NULL DEFAULT 1,
                        sync_status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        company_id INTEGER NOT NULL,
                        rule_id INTEGER NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'ok',
                        message TEXT,
                        ran_at DATETIME NOT NULL,
                        FOREIGN KEY(company_id) REFERENCES companies (id),
                        FOREIGN KEY(rule_id) REFERENCES automation_rules (id)
                    )
                    """
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_automation_runs_company_id "
                    "ON automation_runs (company_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_automation_runs_rule_id "
                    "ON automation_runs (rule_id)"
                )
            )
