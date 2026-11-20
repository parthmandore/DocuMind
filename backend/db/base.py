"""DocuMind Database Setup & Session Management

Provides SQLAlchemy declarative base, sessionmaker, engine creation,
and SQLite foreign key pragma configuration.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.config import config

Base = declarative_base()

def get_engine(db_url: str = None):
    url = db_url or config.database_url
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    
    engine = create_engine(
        url,
        connect_args=connect_args,
        echo=config.debug
    )

    # Enable SQLite foreign key constraints so ON DELETE CASCADE functions
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """FastAPI dependency yielding a database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables and run safe schema migrations."""
    import backend.db.models  # Ensure models are registered with Base
    Base.metadata.create_all(bind=engine)

    # Safe SQLite column migrations for existing databases
    if config.database_url.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                cursor = conn.connection.cursor()
                cursor.execute("PRAGMA table_info(messages)")
                cols = [r[1] for r in cursor.fetchall()]
                if "message_metadata" not in cols:
                    cursor.execute("ALTER TABLE messages ADD COLUMN message_metadata JSON DEFAULT '{}'")
                cursor.close()
        except Exception:
            pass
