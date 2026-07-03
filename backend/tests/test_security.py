import uuid

import pytest

from app.core.security import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_produces_verifiable_but_distinct_hash():
    hashed = hash_password("Sup3r$ecretPass!")
    assert hashed != "Sup3r$ecretPass!"
    assert verify_password("Sup3r$ecretPass!", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_round_trip():
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, role="admin", session_id=session_id)

    payload = decode_token(token, TokenType.ACCESS)

    assert payload["sub"] == str(user_id)
    assert payload["role"] == "admin"
    assert payload["sid"] == str(session_id)
    assert payload["type"] == TokenType.ACCESS


def test_refresh_token_rejected_when_access_expected():
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    token = create_refresh_token(user_id=user_id, session_id=session_id)

    with pytest.raises(InvalidTokenError):
        decode_token(token, TokenType.ACCESS)


def test_garbage_token_is_rejected():
    with pytest.raises(InvalidTokenError):
        decode_token("not-a-real-token", TokenType.ACCESS)
