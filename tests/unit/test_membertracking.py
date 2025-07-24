import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Chat, User
from telegram.constants import ChatMemberStatus
from bot.handlers.membertracking import (
    track_new_members,
    track_left_members,
    track_chat_member_updates,
    update_member_count,
)

class TestMemberTracking(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Common test data
        self.user1 = User(id=123, first_name="User1", is_bot=False)
        self.user2 = User(id=456, first_name="User2", is_bot=False)
        self.host_user = User(id=789, first_name="Host", is_bot=False)
        self.chat = Chat(id=-100123456789, type="supergroup")
        
        # Mock context
        self.context = MagicMock()
        self.context.bot_data = {'db': MagicMock()}
        self.context.bot = MagicMock()
        self.context.bot.edit_message_text = AsyncMock()
        
        # Mock game data
        self.game_data = {
            'id': 'game123',
            'host': '789',  # host_user is the host
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

    @patch('membertracking.get_game_by_group_id')
    @patch('membertracking.update_announcement_with_count')
    async def test_track_new_members(self, mock_update_announcement, mock_get_game):
        # Setup - users join (excluding host)
        update = MagicMock()
        update.message = MagicMock()
        update.message.chat = self.chat
        update.message.new_chat_members = [self.user1, self.user2]
        
        mock_get_game.return_value = self.game_data
        mock_update_announcement.return_value = True
        self.context.bot_data['db'].update_game = MagicMock()
        
        await track_new_members(update, self.context)
        
        # Verify - should add 2 users
        self.context.bot_data['db'].update_game.assert_called_once()
        call_args = self.context.bot_data['db'].update_game.call_args
        self.assertEqual(call_args[0][0], 'game123')
        self.assertEqual(call_args[0][1]['player_count'], 5)  # 3 + 2

    @patch('membertracking.get_game_by_group_id')
    @patch('membertracking.update_announcement_with_count')
    async def test_track_left_members(self, mock_update_announcement, mock_get_game):
        # Setup - user leaves
        update = MagicMock()
        update.message = MagicMock()
        update.message.chat = self.chat
        update.message.left_chat_member = self.user1
        
        mock_get_game.return_value = self.game_data
        mock_update_announcement.return_value = True
        self.context.bot_data['db'].update_game = MagicMock()
        
        # Test
        await track_left_members(update, self.context)
        
        # Verify - should subtract 1 user
        self.context.bot_data['db'].update_game.assert_called_once()
        call_args = self.context.bot_data['db'].update_game.call_args
        self.assertEqual(call_args[0][0], 'game123')
        self.assertEqual(call_args[0][1]['player_count'], 2)  # 3 - 1

    @patch('membertracking.get_game_by_group_id')
    @patch('membertracking.update_announcement_with_count')
    async def test_track_chat_member_updates_ban(self, mock_update_announcement, mock_get_game):
        # Setup - user gets banned
        update = MagicMock()
        update.chat_member = MagicMock()
        update.chat_member.chat = self.chat
        update.chat_member.new_chat_member = MagicMock()
        update.chat_member.new_chat_member.user = self.user1
        update.chat_member.old_chat_member = MagicMock()
        update.chat_member.old_chat_member.status = ChatMemberStatus.MEMBER
        update.chat_member.new_chat_member.status = ChatMemberStatus.BANNED
        
        # Make sure the async mock returns the game data
        mock_get_game.return_value = self.game_data
        mock_update_announcement.return_value = True
        self.context.bot_data['db'].update_game = MagicMock()
        
        # Debug: Print what we're testing
        print(f"Testing status change: {ChatMemberStatus.MEMBER} -> {ChatMemberStatus.BANNED}")
        print(f"User ID: {self.user1.id}, Host ID: {self.game_data['host']}")
        
        await track_chat_member_updates(update, self.context)
        
        # Verify - should subtract 1 user
        self.context.bot_data['db'].update_game.assert_called_once()
        call_args = self.context.bot_data['db'].update_game.call_args
        self.assertEqual(call_args[0][0], 'game123')
        self.assertEqual(call_args[0][1]['player_count'], 2)  # 3 - 1


        @patch('membertracking.update_announcement_with_count')
        async def test_update_member_count(self, mock_update_announcement):
            # Setup
            mock_update_announcement.return_value = True
            self.context.bot_data['db'].update_game = MagicMock()
            
            # Test join
            await update_member_count(self.context, self.game_data, 2, True, [self.user1, self.user2])
            
            # Verify
            self.context.bot_data['db'].update_game.assert_called_once_with('game123', {'player_count': 5})
            mock_update_announcement.assert_called_once()

if __name__ == '__main__':
    unittest.main()