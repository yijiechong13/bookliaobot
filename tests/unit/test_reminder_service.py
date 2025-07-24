import asyncio
import pytest
from freezegun import freeze_time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import pytz
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
    
    @freeze_time("2024-12-24 06:29:00")  # Singapore time equivalent: 2024-12-24 14:29:00 SGT
    @pytest.mark.asyncio
    async def test_schedule_game_reminders_24h_future(self, reminder_service, mock_context, sample_game_data):
        """Test that 24h reminder is scheduled when game is 24+ hours away"""
        game_id = "test_game_123"
        
        # Mock job queue methods
        mock_context.job_queue.get_jobs_by_name.return_value = []
        mock_context.job_queue.run_once = Mock()
        
        await reminder_service.schedule_game_reminders(mock_context, sample_game_data, game_id)
        
        # Verify that run_once was called for 24h reminder
        calls = mock_context.job_queue.run_once.call_args_list
        job_names = [call.kwargs.get('name') for call in calls if 'name' in call.kwargs]
        
        assert f"reminder_24h_{game_id}" in job_names
        print("✅ 24h reminder scheduled successfully")
    
    @freeze_time("2024-12-25 04:29:00")  # Singapore time equivalent: 2024-12-25 12:29:00 SGT
    @pytest.mark.asyncio
    async def test_schedule_game_reminders_2h_future(self, reminder_service, mock_context, sample_game_data):
        """Test that 2h reminder is scheduled when game is 2+ hours away"""
        game_id = "test_game_123"
        
        # Mock job queue methods
        mock_context.job_queue.get_jobs_by_name.return_value = []
        mock_context.job_queue.run_once = Mock()
        
        await reminder_service.schedule_game_reminders(mock_context, sample_game_data, game_id)
        
        # Verify that run_once was called for 2h reminder
        calls = mock_context.job_queue.run_once.call_args_list
        job_names = [call.kwargs.get('name') for call in calls if 'name' in call.kwargs]
        
        assert f"reminder_2h_{game_id}" in job_names
        print("✅ 2h reminder scheduled successfully")
    
    @freeze_time("2024-12-25 16:00:00")  # After game time
    @pytest.mark.asyncio
    async def test_schedule_game_reminders_past_time(self, reminder_service, mock_context, sample_game_data):
        """Test that no reminders are scheduled when game time has passed"""
        game_id = "test_game_123"
        
        # Mock job queue methods
        mock_context.job_queue.get_jobs_by_name.return_value = []
        mock_context.job_queue.run_once = Mock()
        
        await reminder_service.schedule_game_reminders(mock_context, sample_game_data, game_id)
        
        # Verify that run_once was not called (no reminders scheduled)
        mock_context.job_queue.run_once.assert_not_called()
        print("✅ No reminders scheduled for past game")
    
    @pytest.mark.asyncio
    async def test_send_24h_reminder_job_success(self, reminder_service, mock_context, sample_game_data):
        """Test successful execution of 24h reminder job"""
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
    async def test_send_24h_reminder_job_game_closed(self, reminder_service, mock_context, sample_game_data):
        """Test that 24h reminder job skips closed games"""
        game_id = "test_game_123"
        closed_game_data = {**sample_game_data, "status": "closed"}
        
        # Mock job data
        mock_context.job.data = {
            'game_id': game_id,
            'game_data': sample_game_data
        }
        
        # Mock database response with closed game
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = closed_game_data
        
        mock_game_ref = Mock()
        mock_game_ref.get.return_value = mock_doc
        reminder_service.db.db.collection.return_value.document.return_value = mock_game_ref
        
        # Mock the send_24h_reminder method
        reminder_service.send_24h_reminder = AsyncMock()
        
        await reminder_service.send_24h_reminder_job(mock_context)
        
        # Verify send_24h_reminder was NOT called
        reminder_service.send_24h_reminder.assert_not_called()
        print("✅ 24h reminder job correctly skipped closed game")
    
    @pytest.mark.asyncio
    async def test_send_24h_reminder_job_already_sent(self, reminder_service, mock_context, sample_game_data):
        """Test that 24h reminder job skips when reminder already sent"""
        game_id = "test_game_123"
        already_sent_data = {**sample_game_data, "reminder_24h_sent": True}
        
        # Mock job data
        mock_context.job.data = {
            'game_id': game_id,
            'game_data': sample_game_data
        }
        
        # Mock database response
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = already_sent_data
        
        mock_game_ref = Mock()
        mock_game_ref.get.return_value = mock_doc
        reminder_service.db.db.collection.return_value.document.return_value = mock_game_ref
        
        # Mock the send_24h_reminder method
        reminder_service.send_24h_reminder = AsyncMock()
        
        await reminder_service.send_24h_reminder_job(mock_context)
        
        # Verify send_24h_reminder was NOT called
        reminder_service.send_24h_reminder.assert_not_called()
        print("✅ 24h reminder job correctly skipped already sent reminder")
    
    @pytest.mark.asyncio
    async def test_game_start_datetime_parsing(self, reminder_service):
        """Test game datetime parsing"""
        game_data = {
            "date": "25/12/2024",
            "start_time_24": "14:30"
        }
        
        result = await reminder_service.game_start_datetime(game_data)
        
        expected = datetime(2024, 12, 25, 14, 30)
        expected = pytz.timezone("Asia/Singapore").localize(expected)
        
        assert result == expected
        print("✅ Game datetime parsed correctly")
    
    @pytest.mark.asyncio
    async def test_game_start_datetime_invalid_data(self, reminder_service):
        """Test game datetime parsing with invalid data"""
        game_data = {
            "date": "invalid",
            "start_time_24": "14:30"
        }
        
        result = await reminder_service.game_start_datetime(game_data)
        
        assert result is None
        print("✅ Invalid datetime handled correctly")
    
    @pytest.mark.asyncio
    async def test_cancel_game_reminders(self, reminder_service, mock_context):
        """Test cancelling game reminders"""
        game_id = "test_game_123"
        
        # Mock existing jobs
        mock_job_24h = Mock()
        mock_job_2h = Mock()
        
        def mock_get_jobs_by_name(job_name):
            if job_name == f"reminder_24h_{game_id}":
                return [mock_job_24h]
            elif job_name == f"reminder_2h_{game_id}":
                return [mock_job_2h]
            return []
        
        mock_context.job_queue.get_jobs_by_name.side_effect = mock_get_jobs_by_name
        
        await reminder_service.cancel_game_reminders(mock_context, game_id)
        
        # Verify jobs were scheduled for removal
        mock_job_24h.schedule_removal.assert_called_once()
        mock_job_2h.schedule_removal.assert_called_once()
        print("✅ Game reminders cancelled successfully")
    
    @pytest.mark.asyncio
    async def test_schedule_all_existing_reminders(self, reminder_service, mock_context):
        """Test scheduling reminders for all existing games"""
        # Mock database query results
        mock_game_doc1 = Mock()
        mock_game_doc1.id = "game_1"
        mock_game_doc1.to_dict.return_value = {
            "date": "26/12/2024",
            "start_time_24": "15:00",
            "status": "open",
            "reminder_24h_sent": False,
            "reminder_2h_sent": False
        }
        
        mock_game_doc2 = Mock()
        mock_game_doc2.id = "game_2"
        mock_game_doc2.to_dict.return_value = {
            "date": "27/12/2024", 
            "start_time_24": "16:00",
            "status": "open",
            "reminder_24h_sent": True,  # Already sent
            "reminder_2h_sent": True   # Already sent
        }
        
        # Mock query chain
        mock_query = Mock()
        mock_query.stream.return_value = [mock_game_doc1, mock_game_doc2]
        
        mock_collection = Mock()
        mock_collection.where.return_value = mock_query
        
        reminder_service.db.db.collection.return_value = mock_collection
        
        # Mock schedule_game_reminders
        reminder_service.schedule_game_reminders = AsyncMock()
        
        await reminder_service.schedule_all_existing_reminders(mock_context)
        
        # Verify only game_1 had reminders scheduled (game_2 already sent both reminders)
        reminder_service.schedule_game_reminders.assert_called_once_with(
            mock_context, mock_game_doc1.to_dict(), "game_1"
        )
        print("✅ Existing reminders scheduled correctly")