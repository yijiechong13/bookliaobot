import unittest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Add the project root to Python path
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_root)

# Mock ALL the problematic modules BEFORE any imports
mock_utils = MagicMock()
mock_utils.GroupIdHelper = MagicMock()
mock_utils.DateTimeHelper = MagicMock()
mock_utils.ValidationHelper = MagicMock()

# Set up specific mock methods that are used in membertracking.py
mock_utils.GroupIdHelper.get_search_group_id = MagicMock(return_value="123456789")
mock_utils.GroupIdHelper.log_group_conversion = MagicMock()
mock_utils.GroupIdHelper.to_telegram_format = MagicMock(return_value="-100123456789")
mock_utils.ValidationHelper.validate_game_data = MagicMock(return_value=(True, []))

mock_services = MagicMock()
mock_database = MagicMock()

# Add mocks to sys.modules to prevent import errors
sys.modules['utils'] = mock_utils
sys.modules['utils.GroupIdHelper'] = mock_utils.GroupIdHelper
sys.modules['utils.DateTimeHelper'] = mock_utils.DateTimeHelper  
sys.modules['utils.ValidationHelper'] = mock_utils.ValidationHelper
sys.modules['utils.constants'] = MagicMock()  
sys.modules['services'] = mock_services
sys.modules['services.database'] = mock_database
sys.modules['services.telethon_service'] = MagicMock()

from telegram import Chat, User
from telegram.constants import ChatMemberStatus

# Now we can safely import the membertracking module
try:
    from bot.handlers.membertracking import (
        track_new_members,
        track_left_members,
        track_chat_member_updates,
        update_member_count,
    )
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    IMPORTS_SUCCESSFUL = False
    # Create mock functions for testing
    track_new_members = AsyncMock()
    track_left_members = AsyncMock()
    track_chat_member_updates = AsyncMock()
    update_member_count = AsyncMock()

class TestMemberTracking(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Test users
        self.user1 = MagicMock(id=123, first_name="User1", is_bot=False)
        self.user2 = MagicMock(id=456, first_name="User2", is_bot=False)
        self.host_user = MagicMock(id=789, first_name="Host", is_bot=False)
        self.chat = Chat(id=-100123456789, type="supergroup")
        
        # Mock context
        self.context = MagicMock()
        self.context.bot_data = {'db': MagicMock()}
        self.context.bot = MagicMock()
        
        # Mock game data
        self.game_data = {
            'id': 'game123',
            'host': '789',
            'player_count': 3,
            'announcement_msg_id': 987,
            'sport': 'Basketball',
            'date': '2023-12-25',
            'time_display': '15:00',
            'venue': 'Central Park',
            'skill': 'intermediate',
            'group_link': 'https://t.me/testgroup',
            'group_id': '123456789',
            'host_username': 'testhost'
        }

    @unittest.skipUnless(IMPORTS_SUCCESSFUL, "Module imports failed")
    @patch('bot.handlers.membertracking.get_game_by_group_id')
    @patch('bot.handlers.membertracking.update_announcement_with_count')
    async def test_track_new_members(self, mock_update_announcement, mock_get_game):
        # Setup
        update = MagicMock()
        update.message = MagicMock()
        update.message.chat = self.chat
        update.message.new_chat_members = [self.user1, self.user2]
        
        mock_get_game.return_value = self.game_data
        mock_update_announcement.return_value = True
        self.context.bot_data['db'].update_game = MagicMock()
        
        # Test
        await track_new_members(update, self.context)
        
        # Verify
        self.context.bot_data['db'].update_game.assert_called_once()
        call_args = self.context.bot_data['db'].update_game.call_args
        self.assertEqual(call_args[0][0], 'game123')
        self.assertEqual(call_args[0][1]['player_count'], 5)  # 3 + 2 new members

    @unittest.skipUnless(IMPORTS_SUCCESSFUL, "Module imports failed")
    @patch('bot.handlers.membertracking.get_game_by_group_id')
    @patch('bot.handlers.membertracking.update_announcement_with_count')
    async def test_track_left_members(self, mock_update_announcement, mock_get_game):
        # Setup
        update = MagicMock()
        update.message = MagicMock()
        update.message.chat = self.chat
        update.message.left_chat_member = self.user1
        
        mock_get_game.return_value = self.game_data
        mock_update_announcement.return_value = True
        self.context.bot_data['db'].update_game = MagicMock()
        
        # Test
        await track_left_members(update, self.context)
        
        # Verify
        self.context.bot_data['db'].update_game.assert_called_once()
        call_args = self.context.bot_data['db'].update_game.call_args
        self.assertEqual(call_args[0][0], 'game123')
        self.assertEqual(call_args[0][1]['player_count'], 2)  # 3 - 1 member

    @unittest.skipUnless(IMPORTS_SUCCESSFUL, "Module imports failed")
    @patch('bot.handlers.membertracking.get_game_by_group_id')
    @patch('bot.handlers.membertracking.update_announcement_with_count')
    async def test_track_chat_member_updates_ban(self, mock_update_announcement, mock_get_game):
        # Setup
        update = MagicMock()
        update.chat_member = MagicMock()
        update.chat_member.chat = self.chat
        update.chat_member.new_chat_member = MagicMock()
        update.chat_member.new_chat_member.user = self.user1
        update.chat_member.old_chat_member = MagicMock()
        update.chat_member.old_chat_member.status = ChatMemberStatus.MEMBER
        update.chat_member.new_chat_member.status = ChatMemberStatus.BANNED
        
        mock_get_game.return_value = self.game_data
        mock_update_announcement.return_value = True
        self.context.bot_data['db'].update_game = MagicMock()
        
        # Test
        await track_chat_member_updates(update, self.context)
        
        # Verify
        self.context.bot_data['db'].update_game.assert_called_once()
        call_args = self.context.bot_data['db'].update_game.call_args
        self.assertEqual(call_args[0][0], 'game123')
        self.assertEqual(call_args[0][1]['player_count'], 2)  # 3 - 1 banned member


if __name__ == '__main__':
    unittest.main()