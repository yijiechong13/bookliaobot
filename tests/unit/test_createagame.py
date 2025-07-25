import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from telegram import Update, User, Chat, CallbackQuery, Message
from telegram.ext import ContextTypes

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Mock all dependencies before imports
sys.modules['utils'] = MagicMock()
sys.modules['services.telethon_service'] = MagicMock()
sys.modules['utils.constants'] = MagicMock()
sys.modules['fuzzywuzzy'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['telegram'] = MagicMock()
sys.modules['telegram.ext'] = MagicMock()

# Mock constants
mock_constants = sys.modules['utils.constants']
mock_constants.SPORTS_LIST = [("Basketball", "basketball"), ("Football", "football")]
mock_constants.SKILL_LEVELS = ["beginner", "intermediate", "advanced"]
mock_constants.VENUES = {
    "NUS Sports Centre": ["nus sports", "sports centre"],
    "ActiveSG Clementi": ["clementi", "activesg clementi"]
}
mock_constants.BOOKING_URLS = {
    'NUS_FACILITIES': 'https://uci.nus.edu.sg/oca/facility-booking/',
    'ACTIVESG': 'https://members.myactivesg.com/'
}
mock_constants.HOST_MENU = 1
mock_constants.ASK_BOOKING = 2
mock_constants.SPORT = 3
mock_constants.DATE = 4
mock_constants.TIME = 5
mock_constants.VENUE = 6
mock_constants.VENUE_CONFIRM = 7
mock_constants.SKILL = 8
mock_constants.CONFIRMATION = 9
mock_constants.WAITING_BOOKING_CONFIRM = 10

# Mock utils functions
mock_utils = sys.modules['utils']
mock_utils.validate_date_format = MagicMock()
mock_utils.parse_time_input = MagicMock()

# Mock fuzzywuzzy
mock_fuzzywuzzy = sys.modules['fuzzywuzzy']
mock_process = MagicMock()
mock_fuzzywuzzy.process = mock_process

from bot.handlers.createagame import (
    host_game, create_game, handle_venue_response, 
    date_chosen, time_chosen, venue_chosen, 
    venue_confirmation, save_game, after_booking, sport_chosen
)

class TestCreateGame:
    
    @pytest.fixture
    def mock_update(self):
        update = MagicMock(spec=Update)
        update.callback_query = MagicMock(spec=CallbackQuery)
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.effective_user = MagicMock(spec=User)
        update.effective_user.id = 12345
        update.effective_user.username = "testuser"
        return update
    
    @pytest.fixture
    def mock_context(self):
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        context.bot_data = {
            'db': MagicMock(),
            'reminder_service': MagicMock()
        }
        context.bot = MagicMock()
        return context

    @pytest.mark.asyncio
    async def test_handle_venue_response_yes(self, mock_update, mock_context):
        mock_update.callback_query.data = "venue_yes"
        
        result = await handle_venue_response(mock_update, mock_context)
        
        # Verify sports selection is shown
        mock_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_update.callback_query.edit_message_text.call_args
        # Check positional args instead of kwargs
        assert "sport" in call_args[0][0].lower()
        
        assert result == mock_constants.SPORT

    @pytest.mark.asyncio
    async def test_handle_venue_response_no_shows_booking_links(self, mock_update, mock_context):
        mock_update.callback_query.data = "venue_no"
        mock_update.callback_query.message = MagicMock()
        mock_update.callback_query.message.reply_text = AsyncMock()
        
        result = await handle_venue_response(mock_update, mock_context)
        
        # Verify booking links are shown
        mock_update.callback_query.edit_message_text.assert_called_once()
        
        # Verify done booking button is sent
        mock_update.callback_query.message.reply_text.assert_called_once()
        
        assert result == mock_constants.WAITING_BOOKING_CONFIRM

    @pytest.mark.asyncio
    async def test_date_chosen_valid_date(self, mock_context):
        # Create mock update for message
        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "25/12/2025"
        update.message.reply_text = AsyncMock()
        
        # Mock successful validation
        mock_utils.validate_date_format.return_value = (True, "25/12/2025")
        
        result = await date_chosen(update, mock_context)
        
        # Verify date was stored
        assert mock_context.user_data["date"] == "25/12/2025"
        
        # Verify time prompt was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "time" in call_args.lower()
        
        assert result == mock_constants.TIME

    @pytest.mark.asyncio
    async def test_date_chosen_invalid_date(self, mock_context):
        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "invalid-date"
        update.message.reply_text = AsyncMock()
        
        # Mock failed validation
        mock_utils.validate_date_format.return_value = (False, "Invalid date format")
        
        result = await date_chosen(update, mock_context)
        
        # Verify date was not stored
        assert "date" not in mock_context.user_data
        
        # Verify error message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "❌" in call_args
        assert "Invalid date format" in call_args
        
        # Should return to DATE state for retry
        assert result == mock_constants.DATE

    @pytest.mark.asyncio
    async def test_time_chosen_valid_time(self, mock_context):
        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "2pm-4pm"
        update.message.reply_text = AsyncMock()
        
        # Mock successful time parsing
        mock_utils.parse_time_input.return_value = (
            {
                "display_format": "2:00 PM - 4:00 PM",
                "start_time_24": "14:00",
                "end_time_24": "16:00",
                "original_input": "2pm-4pm"
            },
            None  # No error
        )
        
        result = await time_chosen(update, mock_context)
        
        # Verify all time data was stored
        assert mock_context.user_data["time_display"] == "2:00 PM - 4:00 PM"
        assert mock_context.user_data["start_time_24"] == "14:00"
        assert mock_context.user_data["end_time_24"] == "16:00"
        assert mock_context.user_data["time_original"] == "2pm-4pm"
        
        # Verify venue prompt was sent
        update.message.reply_text.assert_called_once()
        assert result == mock_constants.VENUE

    @pytest.mark.asyncio
    async def test_time_chosen_invalid_time(self, mock_context):
        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "invalid-time"
        update.message.reply_text = AsyncMock()
        
        # Mock failed time parsing
        mock_utils.parse_time_input.return_value = (None, "Invalid time format")
        
        result = await time_chosen(update, mock_context)
        
        # Verify no time data was stored
        assert "time_display" not in mock_context.user_data
        
        # Verify error message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "Invalid time format" in call_args
        
        # Should return to TIME state for retry
        assert result == mock_constants.TIME

    @pytest.mark.asyncio
    async def test_venue_chosen_with_matches(self, mock_context):
        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "nus sports"
        update.message.reply_text = AsyncMock()
        
        # Mock fuzzy matching to return matches - need to mock the whole process
        with patch('bot.handlers.createagame.process') as mock_process_patch:
            mock_process_patch.extractOne.return_value = ("NUS Sports Centre", 85)
            
            result = await venue_chosen(update, mock_context)
            
            # Verify suggestions were shown
            update.message.reply_text.assert_called_once()
            call_args = update.message.reply_text.call_args
            # Check positional args
            assert "Did you mean" in call_args[0][0]
            
            assert result == mock_constants.VENUE_CONFIRM

    @pytest.mark.asyncio
    async def test_venue_chosen_no_matches(self, mock_context):
        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "unknown venue"
        update.message.reply_text = AsyncMock()
        
        # Mock fuzzy matching to return low score
        with patch('bot.handlers.createagame.process') as mock_process_patch:
            mock_process_patch.extractOne.return_value = ("Some Venue", 30)
            
            result = await venue_chosen(update, mock_context)
            
            # Verify error message about no matches
            update.message.reply_text.assert_called_once()
            call_args = update.message.reply_text.call_args[0][0]
            assert "Could not find" in call_args
            
            # Should return to VENUE state for retry
            assert result == mock_constants.VENUE

    @pytest.mark.asyncio
    async def test_venue_confirmation_confirm(self, mock_update, mock_context):

        mock_update.callback_query.data = "venue_confirm: NUS Sports Centre"
        
        with patch('bot.handlers.createagame.select_skill') as mock_select_skill:
            mock_select_skill.return_value = mock_constants.SKILL
            
            result = await venue_confirmation(mock_update, mock_context)
            
            # Verify venue was stored
            assert mock_context.user_data["venue"] == "NUS Sports Centre"
            
            # Verify select_skill was called
            mock_select_skill.assert_called_once_with(mock_update, mock_context)
            
            assert result == mock_constants.SKILL

    @pytest.mark.asyncio
    async def test_venue_confirmation_keep_original(self, mock_update, mock_context):
        mock_update.callback_query.data = "venue_keep:My Custom Venue"
        
        with patch('bot.handlers.createagame.select_skill') as mock_select_skill:
            mock_select_skill.return_value = mock_constants.SKILL
            
            result = await venue_confirmation(mock_update, mock_context)
            
            # Verify original venue was stored
            assert mock_context.user_data["venue"] == "My Custom Venue"
            
            # Verify select_skill was called
            mock_select_skill.assert_called_once_with(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_save_game_success_with_group_creation(self, mock_update, mock_context):
        # Setup context data
        mock_context.user_data = {
            "auto_create_group": True,
            "sport": "basketball",
            "date": "25/12/2025",
            "time_display": "2:00 PM - 4:00 PM",
            "venue": "NUS Sports Centre",
            "skill": "intermediate",
            "start_time_24": "14:00",
            "end_time_24": "16:00"
        }
        
        # Mock database operations
        mock_db = MagicMock()
        mock_db.save_game.return_value = "game123"
        mock_db.update_game.return_value = None
        mock_context.bot_data['db'] = mock_db
        
        # Mock telethon service
        with patch('bot.handlers.createagame.telethon_service') as mock_telethon:
            mock_telethon.create_game_group = AsyncMock(return_value={
                "group_link": "https://t.me/testgroup",
                "group_id": "123456789",
                "group_name": "Test Game Group"
            })
            
            # Mock announcement posting
            with patch('bot.handlers.createagame.post_announcement') as mock_post:
                mock_announcement = MagicMock()
                mock_announcement.message_id = 987
                mock_announcement.link = "https://t.me/c/123/987"
                mock_post.return_value = mock_announcement
                
                # Mock reminder service
                mock_context.bot_data['reminder_service'].schedule_game_reminders = AsyncMock()
                
                # Mock the loading message
                mock_loading_msg = MagicMock()
                mock_loading_msg.edit_text = AsyncMock()
                mock_update.callback_query.edit_message_text = AsyncMock(return_value=mock_loading_msg)
                
                # Mock ConversationHandler.END
                with patch('bot.handlers.createagame.ConversationHandler') as mock_conv_handler:
                    mock_conv_handler.END = -1
                    
                    # Mock InlineKeyboardMarkup and InlineKeyboardButton
                    with patch('bot.handlers.createagame.InlineKeyboardMarkup'):
                        with patch('bot.handlers.createagame.InlineKeyboardButton'):
                            
                            result = await save_game(mock_update, mock_context)
                            
                            # Verify database save was called
                            mock_db.save_game.assert_called_once()
                            
                            # Verify game data structure
                            save_call_args = mock_db.save_game.call_args[0][0]
                            assert save_call_args["sport"] == "basketball"
                            assert save_call_args["host"] == mock_update.effective_user.id
                            assert save_call_args["status"] == "open"
                            assert save_call_args["player_count"] == 1
                            assert save_call_args["group_link"] == "https://t.me/testgroup"
                            assert save_call_args["group_id"] == "123456789"
                            
                            # Verify telethon service was called
                            mock_telethon.create_game_group.assert_called_once()
                            
                            # Verify reminders were scheduled
                            mock_context.bot_data['reminder_service'].schedule_game_reminders.assert_called_once()
                            
                            # Verify announcement was posted
                            mock_post.assert_called_once()
                            
                            # Verify user_data was cleared
                            assert len(mock_context.user_data) == 0
                            
                            # Verify return value
                            assert result == -1  # ConversationHandler.END