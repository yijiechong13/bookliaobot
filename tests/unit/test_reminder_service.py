import asyncio
import pytest
from freezegun import freeze_time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import pytz
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

sys.modules['utils'] = Mock()
sys.modules['utils.constants'] = Mock()
sys.modules['utils.datetime_helper'] = Mock()
sys.modules['utils.groupid_helper'] = Mock()
sys.modules['utils.validation_helper'] = Mock()

from bot.services.reminder import ReminderService

class TestReminderService:
    
    @pytest.fixture
    def mock_db(self):
        db = Mock()
        db.db = Mock()
        db.update_game = Mock()
        return db
    
    @pytest.fixture
    def reminder_service(self, mock_db):
        return ReminderService(mock_db)
    
    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.bot = AsyncMock()
        context.job_queue = Mock()
        context.job = Mock()
        return context
    
    @pytest.fixture
    def sample_game_data(self):
        return {
            "date": "25/12/2024",
            "start_time_24": "14:30",
            "sport": "Football",
            "time_display": "2:30 PM",
            "venue": "NUS Sports Hall",
            "skill": "beginner",
            "group_id": "123456789",
            "status": "open",
            "reminder_24h_sent": False,
            "reminder_2h_sent": False
        }
    
    
    @pytest.mark.asyncio
    async def test_send_24h_reminder_(self, reminder_service, mock_context, sample_game_data):
        game_id = "test_game_123"
        
        # Mock job data
        mock_context.job.data = {
            'game_id': game_id,
            'game_data': sample_game_data
        }
        
        # Mock database response
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = sample_game_data
        
        mock_game_ref = Mock()
        mock_game_ref.get.return_value = mock_doc
        reminder_service.db.db.collection.return_value.document.return_value = mock_game_ref
        
        # Mock the send_24h_reminder method
        reminder_service.send_24h_reminder = AsyncMock()
        
        await reminder_service.send_24h_reminder_job(mock_context)
        
        # Verify send_24h_reminder was called
        reminder_service.send_24h_reminder.assert_called_once_with(
            mock_context, sample_game_data, game_id
        )
        print("✅ 24h reminder job executed successfully")
    
    
    @pytest.mark.asyncio
    async def test_send_24h_reminder_with_poll(self, reminder_service, mock_context, sample_game_data):
        game_id = "test_game_123"
        
        # Mock GroupIdHelper - patch where it's imported in reminder.py
        with patch('bot.services.reminder.GroupIdHelper') as mock_group_helper:
            mock_group_helper.to_telegram_format.return_value = -123456789
            
            # Mock poll message
            mock_poll_message = Mock()
            mock_poll_message.message_id = 12345
            mock_context.bot.send_message = AsyncMock()
            mock_context.bot.send_poll = AsyncMock(return_value=mock_poll_message)
            mock_context.bot.pin_chat_message = AsyncMock()
            
            await reminder_service.send_24h_reminder(mock_context, sample_game_data, game_id)
            
            # Verify message was sent
            mock_context.bot.send_message.assert_called_once()
            
            # Verify poll was sent and pinned
            mock_context.bot.send_poll.assert_called_once()
            mock_context.bot.pin_chat_message.assert_called_once()
            
            # Verify database was updated
            reminder_service.db.update_game.assert_called_once_with(
                game_id, {'reminder_24h_sent': True}
            )
        
        print("✅ 24h reminder with poll sent successfully")
    
    @pytest.mark.asyncio 
    async def test_send_2h_reminder_no_poll(self, reminder_service, mock_context, sample_game_data):
        game_id = "test_game_123"
        
        with patch('bot.services.reminder.GroupIdHelper') as mock_group_helper:
            mock_group_helper.to_telegram_format.return_value = -123456789
            
            mock_context.bot.send_message = AsyncMock()
            mock_context.bot.send_poll = AsyncMock()
            
            await reminder_service.send_2h_reminder(mock_context, sample_game_data, game_id)
            
            # Verify message was sent
            mock_context.bot.send_message.assert_called_once()
            
            # Verify no poll was sent
            mock_context.bot.send_poll.assert_not_called()
            
            # Verify database was updated
            reminder_service.db.update_game.assert_called_once_with(
                game_id, {'reminder_2h_sent': True}
            )
        
        print("✅ 2h reminder without poll sent successfully")