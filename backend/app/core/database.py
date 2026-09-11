from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema():
    Base.metadata.create_all(bind=engine)
    if not str(engine.url).startswith("sqlite"):
        return
    statements = [
        "ALTER TABLE app_state ADD COLUMN last_plan_status VARCHAR DEFAULT 'none'",
        "ALTER TABLE app_state ADD COLUMN last_plan_trigger VARCHAR",
        "ALTER TABLE app_state ADD COLUMN active_plan_id VARCHAR",
        "ALTER TABLE coordination_tasks ADD COLUMN plan_id VARCHAR",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass
