from core.services.acl import can_view


def test_acl_single_mode():
    assert can_view(owner_id=1, viewer_id=1, mode="single")
    assert not can_view(owner_id=1, viewer_id=2, mode="single")


def test_acl_multiplayer_mode():
    members = [1, 2]
    assert can_view(owner_id=1, viewer_id=2, mode="multiplayer", members=members)
    assert not can_view(owner_id=1, viewer_id=3, mode="multiplayer", members=members)
