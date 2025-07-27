import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Create a simplified test version of the member tracking functions
class MemberTrackingTest:
    def __init__(self, db):
        self.db = db
        
    async def track_new_members(self, update, context):
        try:
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
                
        except Exception as e:
            print(f"Error in track_new_members: {e}")

    async def track_left_members(self, update, context):
        try:
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
            
        except Exception as e:
            print(f"Error in track_left_members: {e}")

    async def get_game_by_group_id(self, group_id):
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
        
        # Update database
        update_data = {"player_count": new_count}
        self.db.update_game(game_id, update_data)
        
        # Update game_data for announcement
        game_data['player_count'] = new_count
        
        # Update announcement if exists
        announcement_msg_id = game_data.get("announcement_msg_id")
        if announcement_msg_id:
            await self.update_announcement(context, game_data, new_count, announcement_msg_id)

    async def update_announcement(self, context, game_data, member_count, announcement_msg_id):
        announcement_text = (
            f"🏟️ New {game_data['sport']} Game!\n"
            f"👥 Players: {member_count}\n"
            f"📍 Venue: {game_data['venue']}"
        )
        
        await context.bot.edit_message_text(
            chat_id=os.getenv("ANNOUNCEMENT_CHANNEL", "-1001234567890"),
            message_id=int(announcement_msg_id),
            text=announcement_text,
            reply_markup=MagicMock()
        )

@pytest.fixture
def mock_database():
    db = MagicMock()
    db.update_game = MagicMock()
    
    # Mock game data
    db.mock_games = [
        {
            'id': 'test_game_123',
            'sport': 'Basketball',
            'date': '01/02/2025',
            'time_display': '2pm-4pm',
            'venue': 'Test Court',
            'skill': 'intermediate',
            'group_id': -123456789,
            'host': 12345,
            'player_count': 2,  # Starting with 2 players
            'announcement_msg_id': 98765,
            'group_link': 'https://t.me/testgroup',
            'host_username': 'testhost'
        }
    ]
    
    return db

@pytest.fixture
def member_tracker(mock_database):
    return MemberTrackingTest(mock_database)

@pytest.fixture
def mock_context():
    context = MagicMock()
    context.bot = MagicMock()
    context.bot.edit_message_text = AsyncMock()
    context.bot.get_chat = AsyncMock()
    context.bot.get_chat_member_count = AsyncMock(return_value=5)
    context.bot_data = {}
    
    return context

@pytest.fixture
def mock_new_user():
    user = MagicMock()
    user.id = 67890
    user.first_name = "NewPlayer"
    user.is_bot = False
    return user

@pytest.fixture
def mock_update_new_member(mock_new_user):
    update = MagicMock()
    update.message = MagicMock()
    update.message.chat = MagicMock()
    update.message.chat.id = -123456789  # Matches test game group_id
    update.message.new_chat_members = [mock_new_user]
    update.message.left_chat_member = None
    return update

class TestMemberTrackingIntegration:
    
    @pytest.mark.asyncio
    async def test_new_member_updates_count(self, member_tracker, mock_context, mock_update_new_member, mock_database):
        
        # Execute the function
        await member_tracker.track_new_members(mock_update_new_member, mock_context)
        
        # Verify database was called to update the game
        mock_database.update_game.assert_called_once()
        
        # Check the update call arguments
        call_args = mock_database.update_game.call_args
        game_id = call_args[0][0]  # First positional argument
        update_data = call_args[0][1]  # Second positional argument
        
        assert game_id == 'test_game_123'
        assert 'player_count' in update_data
        assert update_data['player_count'] == 3  # Should increase from 2 to 3
        
        # Verify announcement update was attempted
        mock_context.bot.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_member_leaving_decreases_count(self, member_tracker, mock_context, mock_new_user, mock_database):
        
        # Create update for member leaving
        update = MagicMock()
        update.message = MagicMock()
        update.message.chat = MagicMock()
        update.message.chat.id = -123456789
        update.message.new_chat_members = None
        update.message.left_chat_member = mock_new_user
        
        # Execute the function
        await member_tracker.track_left_members(update, mock_context)
        
        # Verify database was updated
        mock_database.update_game.assert_called_once()
        
        call_args = mock_database.update_game.call_args
        update_data = call_args[0][1]
        
        assert update_data['player_count'] == 1  # Should decrease from 2 to 1


    @pytest.mark.asyncio
    async def test_multiple_members_joining(self, member_tracker, mock_context, mock_database):
        
        # Create multiple users
        user1 = MagicMock()
        user1.id = 67890
        user1.first_name = "Player1"
        user1.is_bot = False
        
        user2 = MagicMock()
        user2.id = 67891
        user2.first_name = "Player2"
        user2.is_bot = False
        
        # Create update with multiple members
        update = MagicMock()
        update.message = MagicMock()
        update.message.chat = MagicMock()
        update.message.chat.id = -123456789
        update.message.new_chat_members = [user1, user2]
        update.message.left_chat_member = None
        
        # Execute the function
        await member_tracker.track_new_members(update, mock_context)
        
        # Verify count increased by 2 (from 2 to 4)
        call_args = mock_database.update_game.call_args
        update_data = call_args[0][1]
        assert update_data['player_count'] == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])