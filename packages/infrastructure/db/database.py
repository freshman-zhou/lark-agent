from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from packages.shared.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    # Import models before create_all.
    from packages.infrastructure.db.models.task_model import TaskModel  # noqa: F401
    from packages.infrastructure.db.models.agent_action_model import AgentActionModel  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()