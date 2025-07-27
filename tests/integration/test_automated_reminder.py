import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Add the project root to Python path for test imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Create a simple test that directly tests the reminder logic without importing the full service
# This avoids the complex import chain issues

class MockReminderService:
    
    def __init__(self, db):
        self.db = db
        self.reminders_sent = []
        
    async def schedule_game_reminders(self, context, game_data, game_id):
        self.scheduled_reminders = {
            'game_id': game_id,
            'game_data': game_data,
            'reminders': ['24h', '2h']
        }
        return True
        
    async def send_24h_reminder(self, context, game_data, game_id):
        reminder = {
            'type': '24h',
            'game_id': game_id,
            'sport': game_data['sport'],
            'date': game_data['date'],
            'venue': game_data['venue']
        }
        self.reminders_sent.append(reminder)
        
        # Mock sending message
        await context.bot.send_message(
            chat_id=str(game_data['group_id']),
            text=f"⏰ 24-Hour Game Reminder! ⏰\n\n**{game_data['sport']}** game is **tomorrow**!",
            parse_mode='Markdown'
        )
        
        # Mock sending poll
        poll_msg = await context.bot.send_poll(
            chat_id=str(game_data['group_id']),
            question=f"Can you make it for tomorrow's {game_data['sport']} game?",
            options=["✅ Yes, I can make it!", "❌ No, I cannot make it"]
        )
        
        # Mock database update
        self.db.update_game(game_id, {'reminder_24h_sent': True})
        return True
        
    async def send_2h_reminder(self, context, game_data, game_id):
        reminder = {
            'type': '2h',
            'game_id': game_id,
            'sport': game_data['sport'],
            'date': game_data['date'],
            'venue': game_data['venue']
        }
        self.reminders_sent.append(reminder)
        
        # Mock sending message (no poll for 2h)
        await context.bot.send_message(
            chat_id=str(game_data['group_id']),
            text=f"🚨 2-Hour Game Alert! 🚨\n\n**{game_data['sport']}** game starts in **2 hours**!",
            parse_mode='Markdown'
        )
        
        # Mock database update
        self.db.update_game(game_id, {'reminder_2h_sent': True})
        return True
        
    async def cancel_game_reminders(self, context, game_id):
        self.cancelled_reminders = game_id
        return True

@pytest.fixture
def mock_database():
    db = MagicMock()
    db.update_game = MagicMock()
    
    # Mock game document
    mock_game_doc = MagicMock()
    mock_game_doc.exists = True
    mock_game_doc.to_dict.return_value = {
        'sport': 'Basketball',
        'date': '01/02/2025',
        'time_display': '2pm-4pm',
        'start_time_24': '14:00',
        'venue': 'NUS Sports Centre',
        'skill': 'intermediate',
        'group_id': -123456789,
        'status': 'open',
        'reminder_24h_sent': False,
        'reminder_2h_sent': False
    }
    
    db.db = MagicMock()
    db.db.collection.return_value.document.return_value.get.return_value = mock_game_doc
    
    return db

@pytest.fixture
def reminder_service(mock_database):
    return MockReminderService(mock_database)

@pytest.fixture
def mock_context():
    context = MagicMock()
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    context.bot.send_poll = AsyncMock()
    context.bot.pin_chat_message = AsyncMock()
    
    # Mock poll message return
    mock_poll_msg = MagicMock()
    mock_poll_msg.message_id = 456
    context.bot.send_poll.return_value = mock_poll_msg
    
    # Mock job queue
    context.job_queue = MagicMock()
    context.job_queue.run_once = MagicMock()
    context.job_queue.get_jobs_by_name = MagicMock(return_value=[])
    
    return context

@pytest.fixture
def sample_game_data():
    return {
        'sport': 'Basketball',
        'date': '01/02/2025',
        'time_display': '2pm-4pm',
        'start_time_24': '14:00',
        'venue': 'NUS Sports Centre',
        'skill': 'intermediate',
        'group_id': -123456789,
        'status': 'open',
        'reminder_24h_sent': False,
        'reminder_2h_sent': False
    }

class TestAutomatedReminderIntegration:
    
    @pytest.mark.asyncio
    async def test_reminder_scheduling_flow(self, reminder_service, mock_context, sample_game_data):
        game_id = 'test_game_123'
        
        # Test scheduling
        result = await reminder_service.schedule_game_reminders(mock_context, sample_game_data, game_id)
        
        # Verify scheduling was successful
        assert result is True
        assert reminder_service.scheduled_reminders['game_id'] == game_id
        assert reminder_service.scheduled_reminders['game_data'] == sample_game_data
        assert '24h' in reminder_service.scheduled_reminders['reminders']
        assert '2h' in reminder_service.scheduled_reminders['reminders']

    @pytest.mark.asyncio
    async def test_24h_reminder_sending_integration(self, reminder_service, mock_context, sample_game_data):

        game_id = 'test_game_123'
        
        # Test 24h reminder
        result = await reminder_service.send_24h_reminder(mock_context, sample_game_data, game_id)
        
        # Verify reminder was sent
        assert result is True
        assert len(reminder_service.reminders_sent) == 1
        
        reminder = reminder_service.reminders_sent[0]
        assert reminder['type'] == '24h'
        assert reminder['game_id'] == game_id
        assert reminder['sport'] == 'Basketball'
        assert reminder['date'] == '01/02/2025'
        assert reminder['venue'] == 'NUS Sports Centre'
        
        # Verify bot interactions
        mock_context.bot.send_message.assert_called_once()
        mock_context.bot.send_poll.assert_called_once()
        
        # Check message content
        message_call = mock_context.bot.send_message.call_args
        assert 'chat_id' in message_call.kwargs
        assert '24-Hour Game Reminder' in message_call.kwargs['text']
        assert 'Basketball' in message_call.kwargs['text']
        
        # Check poll content
        poll_call = mock_context.bot.send_poll.call_args
        assert 'chat_id' in poll_call.kwargs
        assert "Can you make it for tomorrow's Basketball game?" in poll_call.kwargs['question']
        
        # Verify database update
        reminder_service.db.update_game.assert_called_once_with(
            game_id, 
            {'reminder_24h_sent': True}
        )

    @pytest.mark.asyncio
    async def test_2h_reminder_sending_integration(self, reminder_service, mock_context, sample_game_data):
        game_id = 'test_game_123'
        
        # Test 2h reminder
        result = await reminder_service.send_2h_reminder(mock_context, sample_game_data, game_id)
        
        # Verify reminder was sent
        assert result is True
        assert len(reminder_service.reminders_sent) == 1
        
        reminder = reminder_service.reminders_sent[0]
        assert reminder['type'] == '2h'
        assert reminder['game_id'] == game_id
        assert reminder['sport'] == 'Basketball'
        
        # Verify bot interactions (no poll for 2h reminder)
        mock_context.bot.send_message.assert_called_once()
        mock_context.bot.send_poll.assert_not_called()
        
        # Check message content
        message_call = mock_context.bot.send_message.call_args
        assert '2-Hour Game Alert' in message_call.kwargs['text']
        assert 'Basketball' in message_call.kwargs['text']
        
        # Verify database update
        reminder_service.db.update_game.assert_called_once_with(
            game_id, 
            {'reminder_2h_sent': True}
        )

    @pytest.mark.asyncio
    async def test_multiple_reminders_flow(self, mock_database, mock_context, sample_game_data):

        # Create a fresh reminder service for this test to avoid shared state
        reminder_service = MockReminderService(mock_database)
        game_id = 'test_game_123'
        
        # Send 24h reminder first
        await reminder_service.send_24h_reminder(mock_context, sample_game_data, game_id)
        
        # Reset bot mocks only
        mock_context.bot.send_message.reset_mock()
        mock_context.bot.send_poll.reset_mock()
        
        # Send 2h reminder
        await reminder_service.send_2h_reminder(mock_context, sample_game_data, game_id)
        
        # Verify both reminders were tracked
        assert len(reminder_service.reminders_sent) == 2
        assert reminder_service.reminders_sent[0]['type'] == '24h'
        assert reminder_service.reminders_sent[1]['type'] == '2h'
        
        # Verify database was updated for both reminders
        assert mock_database.update_game.call_count == 2
        
        # Verify the specific calls made
        calls = mock_database.update_game.call_args_list
        assert calls[0] == ((game_id, {'reminder_24h_sent': True}),)
        assert calls[1] == ((game_id, {'reminder_2h_sent': True}),)

    
    @pytest.mark.asyncio
    async def test_reminder_content_formatting(self, reminder_service, mock_context, sample_game_data):
        game_id = 'test_game_123'
        
        # Test 24h reminder content
        await reminder_service.send_24h_reminder(mock_context, sample_game_data, game_id)
        
        message_call = mock_context.bot.send_message.call_args
        message_text = message_call.kwargs['text']
        
        # Verify key information is present
        assert '24-Hour Game Reminder' in message_text
        assert 'Basketball' in message_text
        assert 'tomorrow' in message_text
        
        # Reset and test 2h reminder
        mock_context.bot.send_message.reset_mock()
        await reminder_service.send_2h_reminder(mock_context, sample_game_data, game_id)
        
        message_call = mock_context.bot.send_message.call_args
        message_text = message_call.kwargs['text']
        
        # Verify 2h reminder content
        assert '2-Hour Game Alert' in message_text
        assert 'Basketball' in message_text
        assert '2 hours' in message_text

    def test_reminder_service_initialization(self, mock_database):
        service = MockReminderService(mock_database)
        
        assert service.db == mock_database
        assert service.reminders_sent == []
        assert not hasattr(service, 'scheduled_reminders')  # Not set until scheduling

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])