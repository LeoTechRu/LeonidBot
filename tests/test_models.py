import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from base import Base
from core.models import TgUser, WebUser, Task


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as sess:
        yield sess


def test_unique_constraints(session):
    tg1 = TgUser(telegram_id=1, username="alice")
    session.add(tg1)
    session.commit()
    session.add(TgUser(telegram_id=2, username="alice"))
    with pytest.raises(Exception):
        session.commit()
    session.rollback()
    session.add(TgUser(telegram_id=1, username="bob"))
    with pytest.raises(Exception):
        session.commit()


def test_web_user_unique_username(session):
    u = WebUser(username="webalice", password_hash="x")
    session.add(u)
    session.flush()
    session.add(WebUser(username="webalice", password_hash="y"))
    with pytest.raises(Exception):
        session.flush()


def test_task_defaults(session):
    tg = TgUser(telegram_id=123, username="tg")
    session.add(tg)
    session.commit()
    task = Task(owner_id=123, title="Test")
    session.add(task)
    session.commit()
    assert task.id is not None
    assert task.is_done is False
