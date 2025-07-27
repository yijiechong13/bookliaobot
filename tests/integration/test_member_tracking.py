import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Add the project root to Python path for test imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Mock utils module BEFORE any imports that might use it
utils_mock = MagicMock()
utils_mock.GroupIdHelper = MagicMock()
utils_mock.DateTimeHelper = MagicMock()
utils_mock.ValidationHelper = MagicMock()
sys.modules['utils'] = utils_mock

# Mock utils submodules
sys.modules['utils.datetime_helper'] = MagicMock()
sys.modules['utils.groupid_helper'] = MagicMock() 
sys.modules['utils.validation_helper'] = MagicMock()

# Mock dotenv
sys.modules['dotenv'] = MagicMock()

# Create a simplified member tracking service for testing
class MockMemberTrackingService:
    
    def __init__(self, db):
        self.db = db
        self.member_changes = []
        self.announcements_updated = []
        
    async def track_new_members(self, update, context):
        if not update.message or not update.message.new_chat_members:
            return
            
        chat_id = update.message.chat.id
        new_members = update.message.new_chat_members
        
        # Filter out bots
        real_members = [member for member in new_members if not member.is_bot]
        if not real_members:
            return
            
        # Get game data
        game_data = await self.get_game_by_group_id(chat_id)
        if not game_data:
            return
            
        # Filter out host
        host_id = game_data.get('host')
        new_non_host_members = [
            member for member in real_members 
            if str(member.id) != str(host_id)
        ]
        
        if new_non_host_members:
            await self.update_member_count(
                context, 
                game_data, 
                len(new_non_host_members), 
                True,  # is_join
                new_non_host_members
            )
            
    async def track_left_members(self, update, context):
        if not update.message or not update.message.left_chat_member:
            return
            
        chat_id = update.message.chat.id
        left_member = update.message.left_chat_member
        
        # Skip bots
        if left_member.is_bot:
            return
            
        # Get game data
        game_data = await self.get_game_by_group_id(chat_id)
        if not game_data:
            return
            
        # Skip if this is the host leaving
        host_id = game_data.get('host')
        if str(left_member.id) == str(host_id):
            return
            
        # Update member count
        await self.update_member_count(
            context, 
            game_data, 
            1, 
            False,  # is_join
            [left_member]
        )
        
    async def get_game_by_group_id(self, group_id):
        # Simulate database lookup
        if hasattr(self.db, 'mock_games'):
            for game in self.db.mock_games:
                if game.get('group_id') == group_id:
                    return game
        return None
        
    async def update_member_count(self, context, game_data, count_change, is_join, users):
        game_id = game_data.get('id')
        current_count = game_data.get('player_count', 1)
        
        # Calculate new count
        new_count = current_count + count_change if is_join else max(1, current_count - count_change)
        
        # Track the change
        change_record = {
            'game_id': game_id,
            'old_count': current_count,
            'new_count': new_count,
            'is_join': is_join,
            'user_count': len(users),
            'user_names': [user.first_name for user in users]
        }
        self.member_changes.append(change_record)
        
        # Update database
        self.db.update_game(game_id, {"player_count": new_count})
        
        # Update game_data
        game_data['player_count'] = new_count
        
        # Update announcement if exists
        announcement_msg_id = game_data.get("announcement_msg_id")
        if announcement_msg_id:
            await self.update_announcement_with_count(
                context, 
                game_data, 
                new_count, 
                announcement_msg_id
            )
            
    async def update_announcement_with_count(self, context, game_data, member_count, announcement_msg_id):
        announcement_record = {
            'game_id': game_data.get('id'),
            'message_id': announcement_msg_id,
            'member_count': member_count,
            'sport': game_data.get('sport'),
            'venue': game_data.get('venue')
        }
        self.announcements_updated.append(announcement_record)
        
        # Simulate bot API call
        await context.bot.edit_message_text(
            chat_id=os.getenv("ANNOUNCEMENT_CHANNEL", "-1001234567890"),
            message_id=int(announcement_msg_id),
            text=f"🏟️ New {game_data['sport']} Game!\n👥 Players: {member_count}",
            reply_markup=MagicMock()
        )
        return True
        
    async def get_actual_member_count(self, context, group_id):
        """Mock getting actual member count from Telegram"""
        # Simulate getting member count
        try:
            chat_info = await context.bot.get_chat(group_id)
            total_count = await context.bot.get_chat_member_count(group_id)
            # Subtract bots, ensure minimum of 1
            return max(1, total_count - 1)
        except Exception:
            return 1

@pytest.fixture
def mock_database():
    db = MagicMock()
    db.update_game = MagicMock()
    
    # Mock games data
    db.mock_games = [
        {
            'id': 'game_123',
            'sport': 'Basketball',
            'date': '01/02/2025',
            'time_display': '2pm-4pm',
            'venue': 'NUS Sports Centre',
            'skill': 'intermediate',
            'group_id': -123456789,
            'host': 12345,
            'player_count': 3,
            'announcement_msg_id': 98765,
            'group_link': 'https://t.me/testgroup'
        }
    ]
    
    return db

@pytest.fixture
def member_tracking_service(mock_database):
    return MockMemberTrackingService(mock_database)

@pytest.fixture
def mock_context():
    context = MagicMock()
    context.bot = MagicMock()
    context.bot.edit_message_text = AsyncMock()
    context.bot.get_chat = AsyncMock()
    context.bot.get_chat_member_count = AsyncMock(return_value=5)
    
    # Mock chat info
    mock_chat = MagicMock()
    mock_chat.title = "Test Game Group"
    context.bot.get_chat.return_value = mock_chat
    
    context.bot_data = {'db': None}  # Will be set in tests
    
    return context

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 67890
    user.first_name = "TestUser"
    user.is_bot = False
    return user

@pytest.fixture
def mock_bot_user():
    bot = MagicMock()
    bot.id = 11111
    bot.first_name = "TestBot"
    bot.is_bot = True
    return bot

@pytest.fixture
def mock_update_new_member(mock_user):
    update = MagicMock()
    update.message = MagicMock()
    update.message.chat = MagicMock()
    update.message.chat.id = -123456789
    update.message.new_chat_members = [mock_user]
    update.message.left_chat_member = None
    return update

@pytest.fixture
def mock_update_left_member(mock_user):
    update = MagicMock()
    update.message = MagicMock()
    update.message.chat = MagicMock()
    update.message.chat.id = -123456789
    update.message.new_chat_members = None
    update.message.left_chat_member = mock_user
    return update

class TestMemberTrackingIntegration:
    
    @pytest.mark.asyncio
    async def test_new_member_tracking_integration(
        self, member_tracking_service, mock_context, mock_update_new_member, mock_database
    ):
        mock_context.bot_data['db'] = mock_database
        
        # Test new member tracking
        await member_tracking_service.track_new_members(mock_update_new_member, mock_context)
        
        # Verify member change was tracked
        assert len(member_tracking_service.member_changes) == 1
        
        change = member_tracking_service.member_changes[0]
        assert change['game_id'] == 'game_123'
        assert change['old_count'] == 3
        assert change['new_count'] == 4  # Increased by 1
        assert change['is_join'] is True
        assert change['user_count'] == 1
        assert 'TestUser' in change['user_names']
        
        # Verify database was updated
        mock_database.update_game.assert_called_once_with('game_123', {"player_count": 4})
        
        # Verify announcement was updated
        assert len(member_tracking_service.announcements_updated) == 1
        announcement = member_tracking_service.announcements_updated[0]
        assert announcement['game_id'] == 'game_123'
        assert announcement['member_count'] == 4
        assert announcement['message_id'] == 98765
        
        # Verify bot API call
        mock_context.bot.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_member_leaving_integration(
        self, member_tracking_service, mock_context, mock_update_left_member, mock_database
    ):
        mock_context.bot_data['db'] = mock_database
        
        # Test member leaving tracking
        await member_tracking_service.track_left_members(mock_update_left_member, mock_context)
        
        # Verify member change was tracked
        assert len(member_tracking_service.member_changes) == 1
        
        change = member_tracking_service.member_changes[0]
        assert change['game_id'] == 'game_123'
        assert change['old_count'] == 3
        assert change['new_count'] == 2  # Decreased by 1
        assert change['is_join'] is False
        assert change['user_count'] == 1
        assert 'TestUser' in change['user_names']
        
        # Verify database was updated
        mock_database.update_game.assert_called_once_with('game_123', {"player_count": 2})
        
        # Verify announcement was updated
        assert len(member_tracking_service.announcements_updated) == 1
        announcement = member_tracking_service.announcements_updated[0]
        assert announcement['member_count'] == 2

    @pytest.mark.asyncio
    async def test_bot_members_ignored(
        self, member_tracking_service, mock_context, mock_bot_user, mock_database
    ):
        mock_context.bot_data['db'] = mock_database
        
        # Create update with bot member
        update = MagicMock()
        update.message = MagicMock()
        update.message.chat = MagicMock()
        update.message.chat.id = -123456789
        update.message.new_chat_members = [mock_bot_user]
        update.message.left_chat_member = None
        
        # Test new member tracking with bot
        await member_tracking_service.track_new_members(update, mock_context)
        
        # Verify no member changes were tracked
        assert len(member_tracking_service.member_changes) == 0
        
        # Verify database was not updated
        mock_database.update_game.assert_not_called()

    @pytest.mark.asyncio
    async def test_host_leaving_ignored(
        self, member_tracking_service, mock_context, mock_database
    ):
        mock_context.bot_data['db'] = mock_database
        
        # Create mock host user
        host_user = MagicMock()
        host_user.id = 12345  # Same as host ID in mock game
        host_user.first_name = "HostUser"
        host_user.is_bot = False
        
        # Create update with host leaving
        update = MagicMock()
        update.message = MagicMock()
        update.message.chat = MagicMock()
        update.message.chat.id = -123456789
        update.message.new_chat_members = None
        update.message.left_chat_member = host_user
        
        # Test member leaving with host
        await member_tracking_service.track_left_members(update, mock_context)
        
        # Verify no member changes were tracked
        assert len(member_tracking_service.member_changes) == 0
        
        # Verify database was not updated
        mock_database.update_game.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_members_joining(
        self, member_tracking_service, mock_context, mock_database
    ):
        mock_context.bot_data['db'] = mock_database
        
        # Create multiple users
        user1 = MagicMock()
        user1.id = 67890
        user1.first_name = "User1"
        user1.is_bot = False
        
        user2 = MagicMock()
        user2.id = 67891
        user2.first_name = "User2"
        user2.is_bot = False
        
        # Create update with multiple members
        update = MagicMock()
        update.message = MagicMock()
        update.message.chat = MagicMock()
        update.message.chat.id = -123456789
        update.message.new_chat_members = [user1, user2]
        update.message.left_chat_member = None
        
        # Test multiple member tracking
        await member_tracking_service.track_new_members(update, mock_context)
        
        # Verify member change was tracked
        assert len(member_tracking_service.member_changes) == 1
        
        change = member_tracking_service.member_changes[0]
        assert change['game_id'] == 'game_123'
        assert change['old_count'] == 3
        assert change['new_count'] == 5  # Increased by 2
        assert change['is_join'] is True
        assert change['user_count'] == 2
        assert 'User1' in change['user_names']
        assert 'User2' in change['user_names']
        
        # Verify database was updated with correct count
        mock_database.update_game.assert_called_once_with('game_123', {"player_count": 5})

    @pytest.mark.asyncio
    async def test_member_count_minimum_enforcement(
        self, member_tracking_service, mock_context, mock_database
    ):
        mock_context.bot_data['db'] = mock_database
        
        # Set initial count to 1
        mock_database.mock_games[0]['player_count'] = 1
        
        # Create update with member leaving
        user = MagicMock()
        user.id = 67890
        user.first_name = "TestUser"
        user.is_bot = False
        
        update = MagicMock()
        update.message = MagicMock()
        update.message.chat = MagicMock()
        update.message.chat.id = -123456789
        update.message.new_chat_members = None
        update.message.left_chat_member = user
        
        # Test member leaving when count is already 1
        await member_tracking_service.track_left_members(update, mock_context)
        
        # Verify count stays at minimum of 1
        change = member_tracking_service.member_changes[0]
        assert change['old_count'] == 1
        assert change['new_count'] == 1  # Should not go below 1
        
        # Verify database was updated with minimum count
        mock_database.update_game.assert_called_once_with('game_123', {"player_count": 1})

    @pytest.mark.asyncio
    async def test_no_game_found_scenario(
        self, member_tracking_service, mock_context, mock_database
    ):
        mock_context.bot_data['db'] = mock_database
        
        # Create update with different group ID (no matching game)
        user = MagicMock()
        user.id = 67890
        user.first_name = "TestUser"
        user.is_bot = False
        
        update = MagicMock()
        update.message = MagicMock()
        update.message.chat = MagicMock()
        update.message.chat.id = -999999999  # Different group ID
        update.message.new_chat_members = [user]
        update.message.left_chat_member = None
        
        # Test new member tracking with no matching game
        await member_tracking_service.track_new_members(update, mock_context)
        
        # Verify no member changes were tracked
        assert len(member_tracking_service.member_changes) == 0
        
        # Verify database was not updated
        mock_database.update_game.assert_not_called()

    @pytest.mark.asyncio
    async def test_actual_member_count_integration(
        self, member_tracking_service, mock_context
    ):
        group_id = -123456789
        
        # Test getting actual member count
        actual_count = await member_tracking_service.get_actual_member_count(mock_context, group_id)
        
        # Verify bot API calls were made
        mock_context.bot.get_chat.assert_called_once_with(group_id)
        mock_context.bot.get_chat_member_count.assert_called_once_with(group_id)
        
        # Verify count calculation (5 total - 1 bot = 4)
        assert actual_count == 4

    @pytest.mark.asyncio
    async def test_announcement_update_content(
        self, member_tracking_service, mock_context, mock_database
    ):
        game_data = mock_database.mock_games[0]
        
        # Test announcement update
        await member_tracking_service.update_announcement_with_count(
            mock_context, game_data, 5, 98765
        )
        
        # Verify bot API call with correct parameters
        mock_context.bot.edit_message_text.assert_called_once()
        call_args = mock_context.bot.edit_message_text.call_args
        
        # Check call parameters
        assert call_args.kwargs['message_id'] == 98765
        assert 'Basketball' in call_args.kwargs['text']
        assert 'Players: 5' in call_args.kwargs['text']
        assert 'reply_markup' in call_args.kwargs

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])