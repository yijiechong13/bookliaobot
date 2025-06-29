import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telethon_service import TelethonService
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.functions.channels import CreateChannelRequest, InviteToChannelRequest, EditAdminRequest

@pytest.fixture
def telethon_service():
    service = TelethonService()
    # Mock environment variables
    with patch.dict('os.environ', {
        'TELEGRAM_API_ID': '12345',
        'TELEGRAM_API_HASH': 'hash',
        'TELEGRAM_PHONE_NUMBER': '+1234567890'
    }):
        yield service

@pytest.mark.asyncio
async def test_initialize_success(telethon_service):
    with patch('telethon.TelegramClient.start', new_callable=AsyncMock) as mock_start:
        # Initialize returns None, but sets initialized=True
        await telethon_service.initialize()
        mock_start.assert_awaited_once()
        assert telethon_service.initialized is True

@pytest.mark.asyncio
async def test_create_game_group_success(telethon_service):
    game_data = {
        "sport": "Basketball",
        "date": "25/12/2025",
        "venue": "NUS Court",
        "time_display": "2pm-4pm",
        "skill": "Intermediate"
    }
    host_user = MagicMock(username="test_user")

    # Create a mock Telegram client
    mock_client = AsyncMock()
    telethon_service.client = mock_client
    telethon_service.initialized = True

    # Mock the return value of CreateChannelRequest
    mock_create_result = MagicMock()
    mock_create_result.chats = [MagicMock(id=123)]

    # Use side_effect to simulate different requests
    mock_client.side_effect = lambda req: {
        CreateChannelRequest: mock_create_result,
        InviteToChannelRequest: True,
        EditAdminRequest: True,
        ExportChatInviteRequest: MagicMock(link="https://t.me/group_link")
    }[type(req)]

    # Mock get_entity
    mock_client.get_entity = AsyncMock(return_value=MagicMock())

    # Call the method
    result = await telethon_service.create_game_group(game_data, host_user)

    # Assertions
    assert result["group_link"] == "https://t.me/group_link"
    assert result["group_id"] == 123
    assert result["bot_added"] is True