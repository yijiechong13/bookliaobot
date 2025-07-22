import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telethon_service import TelethonService
from telethon.tl.functions.channels import CreateChannelRequest, InviteToChannelRequest, EditAdminRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ExportChatInviteRequest

@pytest.fixture
def telethon_service():
    return TelethonService()

@pytest.mark.asyncio
async def test_create_game_group_success(telethon_service):
    game_data = {
        "sport": "Basketball",
        "date": "25/12/2025",
        "venue": "NUS Court",
        "time_display": "2pm-4pm",
        "skill": "Intermediate"
    }
    host_user = MagicMock()
    host_user.username = "test_user"
    host_user.first_name = "Test"
    host_user.id = 12345

    # Create a mock Telegram client
    mock_client = AsyncMock()
    telethon_service.client = mock_client
    telethon_service.initialized = True

    # Mock the return value of CreateChannelRequest
    mock_group_entity = MagicMock()
    mock_group_entity.id = 123456789
    
    mock_create_result = MagicMock()
    mock_create_result.chats = [mock_group_entity]

    # Mock bot and host entities
    mock_bot_entity = MagicMock()
    mock_host_entity = MagicMock()

    # Mock invite link
    mock_invite = MagicMock()
    mock_invite.link = "https://t.me/test_group_link"

    # Set up the mock client to handle different request types
    async def mock_client_call(request):
        if isinstance(request, CreateChannelRequest):
            return mock_create_result
        elif isinstance(request, InviteToChannelRequest):
            return True
        elif isinstance(request, EditAdminRequest):
            return True
        elif isinstance(request, ExportChatInviteRequest):
            return mock_invite
        elif isinstance(request, LeaveChannelRequest):
            return True
        else:
            return True

    # Set up mock client methods
    mock_client.side_effect = mock_client_call
    
    # FIXED: Use AsyncMock for get_entity instead of a regular function
    mock_get_entity = AsyncMock()
    
    async def get_entity_side_effect(identifier):
        if identifier == telethon_service.bot_username:
            return mock_bot_entity
        elif identifier == host_user.id:
            return mock_host_entity
        else:
            return MagicMock()
    
    mock_get_entity.side_effect = get_entity_side_effect
    mock_client.get_entity = mock_get_entity
    
    # Mock send_message
    mock_client.send_message = AsyncMock()

    # Call the method
    result = await telethon_service.create_game_group(game_data, host_user)

    # Assertions
    assert result is not None
    assert result["group_link"] == "https://t.me/test_group_link"
    assert result["group_id"] == 123456789
    assert result["group_name"] == "🏀 Basketball @ Nus Court • 25/12/2025"
    assert result["bot_added"] is True
    assert result["creator_left"] is True

    # Verify that the client was called with the expected requests
    assert mock_client.call_count >= 4  # At least CreateChannel, InviteToChannel, EditAdmin, ExportChatInvite, LeaveChannel
    
    # Verify get_entity was called for bot and host - NOW THIS WILL WORK!
    mock_get_entity.assert_any_call(telethon_service.bot_username)
    mock_get_entity.assert_any_call(host_user.id)
    
    # Verify send_message was called
    mock_client.send_message.assert_called_once()

@pytest.mark.asyncio 
async def test_create_game_group_initialization_required(telethon_service):
    """Test that initialization happens when client is None"""
    game_data = {
        "sport": "Tennis",
        "date": "26/12/2025", 
        "venue": "Tennis Court",
        "time_display": "10am-12pm",
        "skill": "Beginner"
    }
    host_user = MagicMock()
    host_user.username = "host_user"
    host_user.id = 54321

    # Ensure client is None initially
    telethon_service.client = None
    telethon_service.initialized = False
    
    # Mock the initialize method
    with patch.object(telethon_service, 'initialize', new_callable=AsyncMock) as mock_init:
        mock_init.return_value = True
        
        # Set up client after initialization
        mock_client = AsyncMock()
        
        async def setup_after_init():
            telethon_service.client = mock_client
            telethon_service.initialized = True
            
        mock_init.side_effect = setup_after_init
        
        # Mock all the client operations
        mock_group_entity = MagicMock()
        mock_group_entity.id = 987654321
        
        mock_create_result = MagicMock()
        mock_create_result.chats = [mock_group_entity]
        
        mock_invite = MagicMock()
        mock_invite.link = "https://t.me/tennis_group"
        
        async def mock_client_call(request):
            if isinstance(request, CreateChannelRequest):
                return mock_create_result
            elif isinstance(request, ExportChatInviteRequest):
                return mock_invite
            else:
                return True
                
        mock_client.side_effect = mock_client_call
        mock_client.get_entity = AsyncMock(return_value=MagicMock())
        mock_client.send_message = AsyncMock()
        
        # Call the method
        result = await telethon_service.create_game_group(game_data, host_user)
        
        # Verify initialization was called
        mock_init.assert_called_once()
        
        # Verify result
        assert result is not None
        assert result["group_id"] == 987654321

@pytest.mark.asyncio
async def test_create_game_group_failure(telethon_service):
    """Test handling of exceptions during group creation"""
    game_data = {
        "sport": "Football",
        "date": "27/12/2025",
        "venue": "Football Field", 
        "time_display": "4pm-6pm",
        "skill": "Advanced"
    }
    host_user = MagicMock()
    host_user.username = "host_user"
    host_user.id = 11111

    # Set up client that throws an exception
    mock_client = AsyncMock()
    mock_client.side_effect = Exception("Network error")
    
    telethon_service.client = mock_client
    telethon_service.initialized = True

    # Call the method
    result = await telethon_service.create_game_group(game_data, host_user)
    
    # Should return None on failure
    assert result is None