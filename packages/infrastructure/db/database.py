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
    from packages.infrastructure.db.models.task_model import TaskModel  
    from packages.infrastructure.db.models.agent_action_model import AgentActionModel  
    from packages.infrastructure.db.models.task_job_model import TaskJobModel  
    from packages.infrastructure.db.models.processed_event_model import ProcessedEventModel  
    from packages.infrastructure.db.models.artifact_model import ArtifactModel
    from packages.passive_listener.models import ListenerChatMessageModel
    from packages.passive_listener.models import ListenerDetectionRunModel
    from packages.passive_listener.models import ListenerTaskSuggestionModel

    Base.metadata.create_all(bind=engine)


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
