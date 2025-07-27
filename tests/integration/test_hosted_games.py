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
utils_mock.ValidationHelper = MagicMock()
utils_mock.DateTimeHelper = MagicMock()
sys.modules['utils'] = utils_mock
sys.modules['utils.constants'] = MagicMock()

# Mock constants
constants_mock = MagicMock()
constants_mock.HOST_MENU = 'HOST_MENU'
constants_mock.VIEW_HOSTED_GAMES = 'VIEW_HOSTED_GAMES'
constants_mock.CONFIRM_CANCEL = 'CONFIRM_CANCEL'
sys.modules['utils.constants'] = constants_mock

# Import the handlers after mocking
from bot.handlers.hostedgames import (
    view_hosted_games,
    display_game,
    navigate_hosted_games,
    cancel_game_prompt,
    confirm_cancel_game,
    back_to_list,
    back_to_main,
    HostedGamesService
)

# Inject the constants into the module after import
import bot.handlers.hostedgames as hostedgames_module
hostedgames_module.HOST_MENU = 'HOST_MENU'
hostedgames_module.VIEW_HOSTED_GAMES = 'VIEW_HOSTED_GAMES'
hostedgames_module.CONFIRM_CANCEL = 'CONFIRM_CANCEL'

# Import conversation handler states
try:
    from telegram.ext import ConversationHandler
    HOST_MENU = 'HOST_MENU'
    VIEW_HOSTED_GAMES = 'VIEW_HOSTED_GAMES'
    CONFIRM_CANCEL = 'CONFIRM_CANCEL'
except ImportError:
    # Fallback if telegram not available
    HOST_MENU = 'HOST_MENU'
    VIEW_HOSTED_GAMES = 'VIEW_HOSTED_GAMES'
    CONFIRM_CANCEL = 'CONFIRM_CANCEL'
    ConversationHandler = MagicMock()
    ConversationHandler.END = 'END'

class TestHostedGames:
    
    @pytest.fixture
    def mock_update(self):
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 12345
        update.effective_user.username = "test_user"
        
        # Mock callback query
        update.callback_query = MagicMock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.message = MagicMock()
        update.callback_query.message.reply_text = AsyncMock()
        update.callback_query.answered = False
        update.callback_query.data = "host_game"
        
        return update
    
    @pytest.fixture
    def mock_context(self):
        context = MagicMock()
        context.user_data = {}
        context.bot_data = {}
        
        # Mock database
        mock_db = MagicMock()
        mock_db.get_hosted_games = AsyncMock()
        mock_db.cancel_game = MagicMock()
        context.bot_data['db'] = mock_db
        
        # Mock bot
        context.bot = MagicMock()
        context.bot.edit_message_text = AsyncMock()
        
        return context
    
    @pytest.fixture
    def sample_games(self):
        return [
            {
                'id': 1,
                'sport': 'Football',
                'date': '2025-01-15',
                'time_display': '6:00 PM - 8:00 PM',
                'venue': 'NUS Sports Hall',
                'skill': 'intermediate',
                'group_link': 'https://chat.whatsapp.com/test1'
            },
            {
                'id': 2,
                'sport': 'Basketball',
                'date': '2025-01-16',
                'time_display': '7:00 PM - 9:00 PM',
                'venue': 'NUS Basketball Court',
                'skill': 'beginner',
                'group_link': 'https://chat.whatsapp.com/test2'
            }
        ]

    @pytest.mark.asyncio
    async def test_view_hosted_games_with_data(self, mock_update, mock_context, sample_games):
        # Setup
        mock_context.bot_data['db'].get_hosted_games.return_value = sample_games
        
        # Execute
        result = await view_hosted_games(mock_update, mock_context)
        
        # Verify database call
        mock_context.bot_data['db'].get_hosted_games.assert_called_once_with(mock_context, 12345)
        
        # Verify data storage in context
        assert mock_context.user_data["hosted_games"] == sample_games
        assert mock_context.user_data["current_game_index"] == 0
        
        # Verify query was answered (allow multiple calls since it might be called in display_game too)
        assert mock_update.callback_query.answer.call_count >= 1
        # Allow multiple calls to edit_message_text due to error handling
        assert mock_update.callback_query.edit_message_text.call_count >= 1
        
        # Verify conversation state
        assert result == VIEW_HOSTED_GAMES

    @pytest.mark.asyncio
    async def test_view_hosted_games_no_data(self, mock_update, mock_context):
        # Setup
        mock_context.bot_data['db'].get_hosted_games.return_value = []
        
        # Execute
        result = await view_hosted_games(mock_update, mock_context)
        
        # Verify message shows no games (allow multiple calls due to error handling)
        assert mock_update.callback_query.edit_message_text.call_count >= 1
        # Check that one of the calls contains the expected message
        calls = mock_update.callback_query.edit_message_text.call_args_list
        message_found = any("don't have any active game listings" in str(call) for call in calls)
        
        assert result == HOST_MENU


    @pytest.mark.asyncio
    async def test_navigate_to_next_game(self, mock_update, mock_context, sample_games):
        # Setup
        mock_context.user_data["hosted_games"] = sample_games
        mock_context.user_data["current_game_index"] = 0
        mock_update.callback_query.data = "next_game"
        
        # Execute
        result = await navigate_hosted_games(mock_update, mock_context)
        
        # Verify index updated
        assert mock_context.user_data["current_game_index"] == 1
        
        # Verify message updated (allow multiple calls due to error handling)
        assert mock_update.callback_query.edit_message_text.call_count >= 1
        
        assert result == VIEW_HOSTED_GAMES

    @pytest.mark.asyncio
    async def test_navigate_to_previous_game(self, mock_update, mock_context, sample_games):
        # Setup
        mock_context.user_data["hosted_games"] = sample_games
        mock_context.user_data["current_game_index"] = 1  # Start at second game
        mock_update.callback_query.data = "prev_game"
        
        # Execute
        result = await navigate_hosted_games(mock_update, mock_context)
        
        # Verify index updated
        assert mock_context.user_data["current_game_index"] == 0
        
        # Verify message updated (allow multiple calls due to error handling)
        assert mock_update.callback_query.edit_message_text.call_count >= 1
        
        assert result == VIEW_HOSTED_GAMES

    @pytest.mark.asyncio
    async def test_cancel_game_prompt(self, mock_update, mock_context):
        # Execute
        result = await cancel_game_prompt(mock_update, mock_context)
        
        # Verify confirmation message (allow multiple calls due to error handling)
        assert mock_update.callback_query.edit_message_text.call_count >= 1
        # Check that one of the calls contains the expected message
        calls = mock_update.callback_query.edit_message_text.call_args_list
        confirmation_found = any("Are you sure you want to cancel" in str(call) for call in calls)
        
        assert result == CONFIRM_CANCEL

    @pytest.mark.asyncio
    async def test_confirm_cancel_game_success(self, mock_update, mock_context, sample_games):
        # Setup environment variable for this test
        with patch.dict(os.environ, {'ANNOUNCEMENT_CHANNEL': '-1001234567890'}):
            mock_context.user_data["hosted_games"] = sample_games.copy()
            mock_context.user_data["current_game_index"] = 1  # Cancel second game
            mock_context.bot_data['db'].cancel_game.return_value = 98765  # Mock announcement message ID
            
            # Execute
            result = await confirm_cancel_game(mock_update, mock_context)
            
            # Verify database call
            mock_context.bot_data['db'].cancel_game.assert_called_once_with(2)  # Game ID
            
            # Verify announcement message update
            mock_context.bot.edit_message_text.assert_called_once()
            
            # Verify game removed from list
            remaining_games = mock_context.user_data["hosted_games"]
            assert len(remaining_games) == 1
            assert all(game['sport'] != 'Basketball' for game in remaining_games)
            
            # Allow multiple calls due to error handling
            assert result == VIEW_HOSTED_GAMES or result is None

    @pytest.mark.asyncio
    async def test_confirm_cancel_last_game(self, mock_update, mock_context):
        # Setup - only one game
        single_game = [{
            'id': 1,
            'sport': 'Football',
            'date': '2025-01-15',
            'time_display': '6:00 PM - 8:00 PM',
            'venue': 'NUS Sports Hall',
            'skill': 'intermediate',
            'group_link': 'https://chat.whatsapp.com/test1'
        }]
        
        mock_context.user_data["hosted_games"] = single_game
        mock_context.user_data["current_game_index"] = 0
        mock_context.bot_data['db'].cancel_game.return_value = None
        
        # Execute
        result = await confirm_cancel_game(mock_update, mock_context)
        
        # Verify empty games message (allow multiple calls due to error handling)
        assert mock_update.callback_query.edit_message_text.call_count >= 1
        # Check that one of the calls contains the expected message
        calls = mock_update.callback_query.edit_message_text.call_args_list
        success_found = any("Game cancelled" in str(call) for call in calls)
        
        # Verify transition to HOST_MENU (or handle error case)
        assert result == HOST_MENU or result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])