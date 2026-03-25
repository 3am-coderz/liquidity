from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def run_startup_migrations() -> None:
    binary_type = "BYTEA" if engine.dialect.name == "postgresql" else "BLOB"
    additions = {
        "invoice_file_name": "VARCHAR(255)",
        "invoice_content_type": "VARCHAR(255)",
        "invoice_data": binary_type,
        "vendor_aggression": "VARCHAR(30)",
        "blocks_revenue": "BOOLEAN",
    }

    with engine.begin() as connection:
        inspector = inspect(connection)
        if "payables" not in inspector.get_table_names():
            return

        existing_columns = {column["name"] for column in inspector.get_columns("payables")}
        for column_name, column_type in additions.items():
            if column_name in existing_columns:
                continue
            connection.execute(text(f"ALTER TABLE payables ADD COLUMN {column_name} {column_type}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
