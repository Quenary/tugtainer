from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status

from backend.modules.auth.auth_util import Config, is_authorized


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "disable_auth, mock_provider, provider_disabled, provider_authorized, expected",
    [
        # Auth disabled -> Returns True
        (True, None, False, False, True),
        # Auth enabled, no active provider -> Raises 401
        (
            False,
            None,
            False,
            False,
            HTTPException(status_code=status.HTTP_401_UNAUTHORIZED),
        ),
        # Auth enabled, provider active (in token), BUT disabled in config -> Raises 403
        (
            False,
            MagicMock(),
            True,
            False,
            HTTPException(status_code=status.HTTP_403_FORBIDDEN),
        ),
        # Auth enabled, provider active and authorized -> Returns True
        (False, MagicMock(), False, True, True),
        # Auth enabled, Provider active and NOT authorized -> Raises 401
        (
            False,
            MagicMock(),
            False,
            False,
            HTTPException(status_code=status.HTTP_401_UNAUTHORIZED),
        ),
    ],
)
@patch("backend.modules.auth.auth_util.active_auth_provider")
async def test_is_authorized(
    mock_active_auth_provider,
    disable_auth,
    mock_provider,
    provider_disabled,
    provider_authorized,
    expected,
):
    with patch.object(Config, "DISABLE_AUTH", disable_auth):
        if mock_provider:
            mock_provider.raise_of_disabled = AsyncMock()
            if provider_disabled:
                mock_provider.raise_of_disabled.side_effect = HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN
                )

            if isinstance(expected, HTTPException):
                mock_provider.is_authorized = AsyncMock(
                    side_effect=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
                )
            else:
                mock_provider.is_authorized = AsyncMock(
                    return_value=provider_authorized
                )

        mock_active_auth_provider.return_value = mock_provider

        mock_request = MagicMock()

        if isinstance(expected, HTTPException):
            with pytest.raises(HTTPException) as exc_info:
                await is_authorized(mock_request)

            assert exc_info.value.status_code == expected.status_code
        else:
            result = await is_authorized(mock_request)
            assert result is expected

        if not disable_auth:
            mock_active_auth_provider.assert_called_once_with(mock_request)
