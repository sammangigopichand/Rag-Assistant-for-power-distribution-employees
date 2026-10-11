"""Add role and checklist ownership columns to an existing database."""
from sqlalchemy import inspect, text
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import engine
from app.admin_config import configured_admin_emails


def migrate():
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        if "users" in tables and "role" not in {c["name"] for c in inspector.get_columns("users")}:
            connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'employee'"))
        if "work_processes" in tables and "created_by" not in {c["name"] for c in inspector.get_columns("work_processes")}:
            connection.execute(text("ALTER TABLE work_processes ADD COLUMN created_by INTEGER REFERENCES users(id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_work_processes_created_by ON work_processes (created_by)"))
        if "work_processes" in tables:
            process_columns = {c["name"] for c in inspector.get_columns("work_processes")}
            if "prerequisites" not in process_columns:
                connection.execute(text("ALTER TABLE work_processes ADD COLUMN prerequisites TEXT"))
            if "safety_notes" not in process_columns:
                connection.execute(text("ALTER TABLE work_processes ADD COLUMN safety_notes TEXT"))
            if "status" not in process_columns:
                connection.execute(text("ALTER TABLE work_processes ADD COLUMN status VARCHAR(24) NOT NULL DEFAULT 'ready'"))
        if "work_steps" in tables and "source_document" not in {c["name"] for c in inspector.get_columns("work_steps")}:
            connection.execute(text("ALTER TABLE work_steps ADD COLUMN source_document VARCHAR(300)"))
        admin_emails = configured_admin_emails()
        if admin_emails and "users" in tables:
            for admin_email in admin_emails:
                connection.execute(
                    text("UPDATE users SET role = 'admin' WHERE lower(email) = :email"),
                    {"email": admin_email},
                )
    print("Role and checklist ownership migration complete.")


if __name__ == "__main__":
    migrate()
