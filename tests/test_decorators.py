import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import decorators
from models import UserRole
from contextlib import asynccontextmanager


def make_message():
    return SimpleNamespace(
        from_user=SimpleNamespace(
            id=1,
            username='user',
            first_name='First',
            last_name='Last',
            language_code='en',
            is_premium=False
        ),
        chat=SimpleNamespace(id=100, title='chat', type='private'),
        answer=AsyncMock()
    )


def test_role_required_allows(monkeypatch):
    called = False

    async def handler(message):
        nonlocal called
        called = True
        return 'ok'

    message = make_message()

    class FakeService:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
        async def get_or_create_user(self, *args, **kwargs):
            return SimpleNamespace(role=UserRole.admin.value), False

    @asynccontextmanager
    async def fake_session():
        yield None

    monkeypatch.setattr(decorators, 'get_session', fake_session)
    monkeypatch.setattr(decorators, 'UserService', lambda session: FakeService())

    async def run():
        wrapped = decorators.role_required(UserRole.single)(handler)
        await wrapped(message)

    asyncio.run(run())
    assert called
    message.answer.assert_not_called()


def test_role_required_denies(monkeypatch):
    called = False

    async def handler(message):
        nonlocal called
        called = True
        return 'ok'

    message = make_message()

    class FakeService:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
        async def get_or_create_user(self, *args, **kwargs):
            return SimpleNamespace(role=UserRole.single.value), False

    @asynccontextmanager
    async def fake_session():
        yield None

    monkeypatch.setattr(decorators, 'get_session', fake_session)
    monkeypatch.setattr(decorators, 'UserService', lambda session: FakeService())

    async def run():
        wrapped = decorators.role_required(UserRole.admin)(handler)
        await wrapped(message)

    asyncio.run(run())
    assert not called
    message.answer.assert_called_once()


def test_group_required_adds_user(monkeypatch):
    called = False

    async def handler(message):
        nonlocal called
        called = True
        return 'ok'

    message = make_message()

    class FakeService:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
        async def get_or_create_group(self, *args, **kwargs):
            return SimpleNamespace(), False
        async def is_user_in_group(self, *args, **kwargs):
            return False
        async def add_user_to_group(self, *args, **kwargs):
            return True, 'added'

    @asynccontextmanager
    async def fake_session():
        yield None

    monkeypatch.setattr(decorators, 'get_session', fake_session)
    monkeypatch.setattr(decorators, 'UserService', lambda session: FakeService())

    async def run():
        wrapped = await decorators.group_required(handler)
        await wrapped(message)

    asyncio.run(run())
    assert called
    message.answer.assert_not_called()


def test_group_required_add_user_fail(monkeypatch):
    called = False

    async def handler(message):
        nonlocal called
        called = True
        return 'ok'

    message = make_message()

    class FakeService:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
        async def get_or_create_group(self, *args, **kwargs):
            return SimpleNamespace(), False
        async def is_user_in_group(self, *args, **kwargs):
            return False
        async def add_user_to_group(self, *args, **kwargs):
            return False, 'error'

    @asynccontextmanager
    async def fake_session():
        yield None

    monkeypatch.setattr(decorators, 'get_session', fake_session)
    monkeypatch.setattr(decorators, 'UserService', lambda session: FakeService())

    async def run():
        wrapped = await decorators.group_required(handler)
        await wrapped(message)

    asyncio.run(run())
    assert not called
    message.answer.assert_called_once()
