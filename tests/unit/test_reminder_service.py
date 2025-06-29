import asyncio
import pytest
from freezegun import freeze_time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import pytz
from reminder import ReminderService

class TestReminderService:
    
    #creates mock version of database 
    @pytest.fixture
    def mock_db(self):
        db = Mock()
        db.db = Mock()
        return db
    
    #mock version of reminder service object 
    @pytest.fixture
    def reminder_service(self, mock_db):
        return ReminderService(mock_db)
    
    
    @freeze_time("2024-12-24 14:30:00", tz_offset=8)  # 24 hours before
    def test_should_send_24h_reminder_true(self, reminder_service):
        game_data = {"reminder_24h_sent": False}
        time_until_game = timedelta(hours=24)
        
        result = asyncio.run(
            reminder_service._should_send_24h_reminder(game_data, time_until_game, "test_id")
        )
        
        assert result is True
    
    def test_should_send_24h_reminder_already_sent(self, reminder_service):
        game_data = {"reminder_24h_sent": True}
        time_until_game = timedelta(hours=24)
        
        result = asyncio.run(
            reminder_service._should_send_24h_reminder(game_data, time_until_game, "test_id")
        )
        
        assert result is False
    
    @freeze_time("2024-12-25 12:00:00", tz_offset=8)  # 2 hours before
    def test_should_send_2h_reminder_true(self, reminder_service):
        game_data = {"reminder_2h_sent": False}
        time_until_game = timedelta(hours=2)
        
        result = asyncio.run(
            reminder_service._should_send_2h_reminder(game_data, time_until_game, "test_id")
        )
        
        assert result is True