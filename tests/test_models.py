import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from base import Base
from models import User, Group, Channel, UserRole, GroupType, ChannelType


@pytest.fixture()
def session():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_user_default_role(session):
    user = User(id=1, telegram_id=1, first_name='Test')
    session.add(user)
    session.flush()
    assert user.role == UserRole.single.value


def test_user_photo_url(session):
    user = User(id=2, telegram_id=2, first_name='Test', photo_url='http://example.com/photo.jpg')
    session.add(user)
    session.flush()
    assert user.photo_url == 'http://example.com/photo.jpg'


def test_group_default_type(session):
    group = Group(id=1, telegram_id=1, title='Group')
    session.add(group)
    session.flush()
    assert group.type == GroupType.private


def test_channel_default_type(session):
    channel = Channel(id=1, telegram_id=1, title='Channel')
    session.add(channel)
    session.flush()
    assert channel.type == ChannelType.channel


def test_enum_values():
    assert UserRole.admin > UserRole.moderator > UserRole.multiplayer > UserRole.single > UserRole.ban
    assert GroupType.private.value == 'private'
    assert ChannelType.supergroup.value == 'supergroup'
