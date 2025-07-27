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
utils_mock.is_game_expired = MagicMock(return_value=False)
utils_mock.validate_date_format = MagicMock()
utils_mock.parse_time_input = MagicMock()
utils_mock.ValidationHelper = MagicMock()
utils_mock.DateTimeHelper = MagicMock()
sys.modules['utils'] = utils_mock

# Mock utils submodules
sys.modules['utils.datetime_helper'] = MagicMock()
sys.modules['utils.groupid_helper'] = MagicMock() 
sys.modules['utils.validation_helper'] = MagicMock()

# Mock utils.constants
constants_mock = MagicMock()
constants_mock.SPORT_EMOJIS = {"Basketball": "🏀", "Football": "⚽", "Tennis": "🎾"}
constants_mock.VENUES = {'NUS Sports Centre': ['nus sports', 'sports center']}
sys.modules['utils.constants'] = constants_mock

# Now we can safely import from bot.handlers
from bot.handlers.createagame import (
    host_game,
    create_game,
    handle_venue_response,
    after_booking,
    sport_chosen,
    date_chosen,
    time_chosen,
    venue_chosen,
    venue_confirmation,
    select_skill,
    skill_chosen,
    save_game
)

# Import services directly (like in test_reminder_service.py)
from bot.services.database import GameDatabase
from bot.services.telethon_service import telethon_service
from bot.services.reminder import ReminderService
from bot.services.venue import VenueNormalizer


class TestGameCreationFlow:
    
    @pytest.fixture
    def mock_context(self):
        context = MagicMock()
        context.bot_data = {
            'db': MagicMock(spec=GameDatabase),
            'telethon_service': MagicMock(spec=telethon_service),
            'reminder_service': MagicMock(spec=ReminderService)
        }
        context.user_data = {}
        context.bot = MagicMock()
        # Make bot methods async
        context.bot.send_message = AsyncMock()
        return context

    @pytest.fixture 
    def mock_update(self):
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 12345
        update.effective_user.username = "test_user"
        
        # Make callback_query methods async
        update.callback_query = MagicMock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        
        # Add message property to callback_query for venue booking test
        update.callback_query.message = MagicMock()
        update.callback_query.message.reply_text = AsyncMock()
        
        # Make message methods async
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        return update

    @pytest.mark.asyncio
    async def test_host_game_selection(self, mock_update, mock_context):
        # Test the initial host game selection
        await host_game(mock_update, mock_context)
        
        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_update.callback_query.edit_message_text.call_args
        text = call_args[1]['text'] if 'text' in call_args[1] else call_args[0][0]
        assert "Host a Game" in text
        # Update these assertions based on the actual text in your handler
        assert "Choose an option" in text

    @pytest.mark.asyncio
    async def test_create_game_flow(self, mock_update, mock_context):
        # Test the create game initiation
        await create_game(mock_update, mock_context)
        
        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_update.callback_query.edit_message_text.call_args
        text = call_args[1]['text'] if 'text' in call_args[1] else call_args[0][0]
        assert "Do you already have a venue booked?" in text
        assert mock_context.user_data["auto_create_group"] == True

    @pytest.mark.asyncio
    async def test_venue_booking_handling(self, mock_update, mock_context):
        # Mock the context.bot.delete_message method
        mock_context.bot.delete_message = AsyncMock()
        
        # Test "yes" path
        mock_update.callback_query.data = "venue_yes"
        await handle_venue_response(mock_update, mock_context)
        
        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_update.callback_query.edit_message_text.call_args
        text = call_args[1]['text'] if 'text' in call_args[1] else call_args[0][0]
        assert "Which sport are you hosting?" in text
        
        # Test the "no" path
        mock_update.callback_query.data = "venue_no"
        mock_update.callback_query.answer.reset_mock()
        mock_update.callback_query.edit_message_text.reset_mock()
        
        # Mock the booking_msg return value
        mock_booking_msg = MagicMock()
        mock_booking_msg.message_id = 123
        mock_booking_msg.chat_id = 456
        mock_update.callback_query.edit_message_text.return_value = mock_booking_msg
        
        await handle_venue_response(mock_update, mock_context)
        
        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_text.assert_called_once()
        mock_update.callback_query.message.reply_text.assert_called_once()
        
        # Check that booking message data is stored
        assert mock_context.user_data["booking_msg_id"] == 123
        assert mock_context.user_data["booking_chat_id"] == 456

    @pytest.mark.asyncio
    async def test_sport_selection(self, mock_update, mock_context):
        # Test sport selection
        mock_update.callback_query.data = "basketball"
        await sport_chosen(mock_update, mock_context)
        
        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_update.callback_query.edit_message_text.call_args
        text = call_args[1]['text'] if 'text' in call_args[1] else call_args[0][0]
        assert "Please enter the game date" in text
        assert mock_context.user_data["sport"] == "basketball"

    @pytest.mark.asyncio
    async def test_date_input_validation(self, mock_update, mock_context):
        # Test valid date input
        mock_update.message.text = "01/01/2025"
        with patch('bot.handlers.createagame.validate_date_format', return_value=(True, "01/01/2025")):
            await date_chosen(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        text = call_args[1] if isinstance(call_args[1], str) else call_args[0][0]
        assert "What time is the game?" in text
        assert mock_context.user_data["date"] == "01/01/2025"

        # Test invalid date input
        mock_update.message.reply_text.reset_mock()
        mock_update.message.text = "invalid date"
        with patch('bot.handlers.createagame.validate_date_format', return_value=(False, "Invalid date format")):
            result = await date_chosen(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        text = call_args[1] if isinstance(call_args[1], str) else call_args[0][0]
        assert "Invalid date format" in text

    @pytest.mark.asyncio
    async def test_time_input_validation(self, mock_update, mock_context):
        # Test valid time input
        mock_update.message.text = "2pm-4pm"
        time_data = {
            "original_input": "2pm-4pm",
            "start_time_24": "14:00",
            "end_time_24": "16:00",
            "display_format": "2pm-4pm"
        }
        with patch('bot.handlers.createagame.parse_time_input', return_value=(time_data, None)):
            await time_chosen(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        text = call_args[1] if isinstance(call_args[1], str) else call_args[0][0]
        assert "Enter the venue/location" in text
        assert mock_context.user_data["time_display"] == "2pm-4pm"
        assert mock_context.user_data["start_time_24"] == "14:00"
        assert mock_context.user_data["end_time_24"] == "16:00"

        # Test invalid time input
        mock_update.message.reply_text.reset_mock()
        mock_update.message.text = "invalid time"
        with patch('bot.handlers.createagame.parse_time_input', return_value=(None, "Invalid time format")):
            result = await time_chosen(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        text = call_args[1] if isinstance(call_args[1], str) else call_args[0][0]
        assert "Invalid time format" in text

    @pytest.mark.asyncio
    async def test_venue_input_and_confirmation(self, mock_update, mock_context):
        # Test venue input with suggestions
        mock_update.message.text = "nus sports center"
        with patch('bot.handlers.createagame.VENUES', {'NUS Sports Centre': ['nus sports', 'sports center']}):
            await venue_chosen(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        text = call_args[0][0] if call_args[0] else call_args[1]['text']
        assert "Did you mean one of these venues?" in text

        # Test venue confirmation
        mock_update.callback_query.data = "venue_confirm:NUS Sports Centre"
        await venue_confirmation(mock_update, mock_context)
        
        mock_update.callback_query.answer.assert_called()
        mock_update.callback_query.edit_message_text.assert_called()
        call_args = mock_update.callback_query.edit_message_text.call_args
        text = call_args[1]['text'] if 'text' in call_args[1] else call_args[0][0]
        assert "Venue selected: NUS Sports Centre" in text
        assert mock_context.user_data["venue"] == "NUS Sports Centre"

    @pytest.mark.asyncio
    async def test_skill_selection(self, mock_update, mock_context):
        # Set up user data that skill_chosen expects
        mock_context.user_data = {
            "sport": "basketball",
            "date": "01/01/2025",
            "time_display": "2pm-4pm",
            "venue": "NUS Sports Centre"
        }
        
        # Test skill selection
        mock_update.callback_query.data = "intermediate"
        await skill_chosen(mock_update, mock_context)
        
        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_update.callback_query.edit_message_text.call_args
        text = call_args[1]['text'] if 'text' in call_args[1] else call_args[0][0]
        assert "New Game Listing" in text
        assert mock_context.user_data["skill"] == "intermediate"

    @pytest.mark.asyncio
    async def test_game_confirmation_and_saving(self, mock_update, mock_context):
        # Prepare complete game data
        mock_context.user_data = {
            "sport": "basketball",
            "date": "01/01/2025",
            "time_display": "2pm-4pm",
            "start_time_24": "14:00",
            "end_time_24": "16:00",
            "venue": "NUS Sports Centre",
            "skill": "intermediate",
            "auto_create_group": True
        }

        # Mock the Telethon service to avoid actual connection
        with patch('bot.handlers.createagame.telethon_service') as mock_telethon:
            mock_telethon.create_game_group = AsyncMock(return_value={
                "group_link": "https://t.me/testgroup",
                "group_id": -123456789,
                "group_name": "Test Group",
                "bot_added": True,
                "creator_left": True
            })
            
            # Mock database save
            mock_context.bot_data['db'].save_game.return_value = "test_game_id"
            mock_context.bot_data['db'].update_game = MagicMock()

            # Mock reminder service
            mock_context.bot_data['reminder_service'].schedule_game_reminders = AsyncMock()

            # Mock announcement
            mock_message = MagicMock()
            mock_message.message_id = 123
            mock_message.link = "https://t.me/announcement/123"
            mock_context.bot.send_message.return_value = mock_message

            # Test game confirmation
            mock_update.callback_query.data = "confirm_game"
            await save_game(mock_update, mock_context)

            # Verify query.answer() was called
            mock_update.callback_query.answer.assert_called_once()

            # Verify group creation
            mock_telethon.create_game_group.assert_called_once()

            # Verify database save
            mock_context.bot_data['db'].save_game.assert_called_once()
            mock_context.bot_data['db'].update_game.assert_called_once_with(
                "test_game_id",
                {"announcement_msg_id": 123}
            )

            # Verify reminders scheduled
            mock_context.bot_data['reminder_service'].schedule_game_reminders.assert_called_once()

            # Verify final message - the handler calls edit_message_text multiple times
            # so we check that it was called at least once, and check the final call
            assert mock_update.callback_query.edit_message_text.call_count >= 2
            
            # Check the final call contains the success message
            final_call = mock_update.callback_query.edit_message_text.call_args_list[-1]
            final_text = final_call[1]['text'] if 'text' in final_call[1] else final_call[0][0]
            assert "Group 'Test Group' created and announced" in final_text