import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from savegame import GameDatabase
from telegram.ext import ContextTypes
import os

@pytest.fixture
def mock_firestore():
    with patch('savegame.firestore.client') as mock:
        yield mock.return_value

@pytest.fixture
def game_database(mock_firestore):
    with patch.dict(os.environ, {'FIREBASE_CREDENTIALS': 'test_credentials.json'}):
        db = GameDatabase()
        db.db = mock_firestore
        return db

@pytest.fixture
def sample_game_data():
    return {
        "sport": "Basketball",
        "date": "25/12/2025",
        "venue": "NUS Court",
        "time_display": "2pm-4pm",
        "skill": "Intermediate",
        "host": "user123",
        "status": "open"
    }

def test_save_game(game_database, sample_game_data):
    mock_doc_ref = MagicMock()
    mock_doc_ref.id = "game123"
    game_database.db.collection.return_value.document.return_value = mock_doc_ref
    
    game_id = game_database.save_game(sample_game_data)
    
    assert game_id == "game123"
    game_database.db.collection.assert_called_with("game")
    mock_doc_ref.set.assert_called_once()
    assert "created_at" in mock_doc_ref.set.call_args[0][0]

def test_update_game_success(game_database):
    mock_doc_ref = MagicMock()
    game_database.db.collection.return_value.document.return_value = mock_doc_ref
    
    with patch('builtins.print') as mock_print:
        game_database.update_game("game123", {"player_count": 5})
    
    mock_doc_ref.update.assert_called_with({"player_count": 5})
    mock_print.assert_called_with("✅ Updated game game123")

def test_update_game_failure(game_database):
    mock_doc_ref = MagicMock()
    mock_doc_ref.update.side_effect = Exception("DB error")
    game_database.db.collection.return_value.document.return_value = mock_doc_ref
    
    with patch('builtins.print') as mock_print:
        game_database.update_game("game123", {"player_count": 5})
    
    mock_print.assert_called_with("❌ Error updating game game123: DB error")

@pytest.mark.asyncio
async def test_get_hosted_games(game_database):
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_game = MagicMock()
    mock_game.id = "game123"
    mock_game.to_dict.return_value = {"sport": "Basketball", "host": "user123"}
    mock_game.reference = MagicMock()
    
    game_database.db.collection.return_value.where.return_value.where.return_value.stream.return_value = [mock_game]
    
    with patch.object(game_database, 'close_expired_games', new_callable=AsyncMock) as mock_close:
        mock_close.return_value = 0
        games = await game_database.get_hosted_games(mock_context, "user123")
    
    assert len(games) == 1
    assert games[0]["id"] == "game123"
    mock_close.assert_awaited_once_with(mock_context)

def test_cancel_game_success(game_database):
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"announcement_msg_id": "msg123"}
    mock_doc_ref = MagicMock()
    mock_doc_ref.get.return_value = mock_doc
    game_database.db.collection.return_value.document.return_value = mock_doc_ref
    
    with patch('builtins.print') as mock_print:
        result = game_database.cancel_game("game123")
    
    assert result == "msg123"
    mock_doc_ref.update.assert_called_once()
    mock_print.assert_called_with("✅ Cancelled game game123")

@pytest.mark.asyncio
async def test_close_expired_games(game_database):
    mock_expired_game = MagicMock()
    mock_expired_game.id = "expired123"
    mock_expired_game.to_dict.return_value = {
        "date": "01/01/2025",
        "end_time_24": "12:00",
        "announcement_msg_id": "msg123"
    }
    mock_expired_game.reference = MagicMock()
    
    mock_active_game = MagicMock()
    mock_active_game.to_dict.return_value = {
        "date": "01/01/2030",
        "end_time_24": "12:00"
    }
    
    game_database.db.collection.return_value.where.return_value.stream.return_value = [mock_expired_game, mock_active_game]
    
    with patch('savegame.is_game_expired', side_effect=[True, False]), \
         patch.object(game_database, '_update_expired_announcement', new_callable=AsyncMock) as mock_update:
        
        count = await game_database.close_expired_games(MagicMock())
        
        assert count == 1
        mock_expired_game.reference.update.assert_called_once()
        mock_update.assert_awaited_once()

@pytest.mark.asyncio
async def test_update_expired_announcement(game_database):
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    
    game_data = {
        "sport": "Basketball",
        "venue": "NUS",
        "time_display": "2pm"
    }
    
    with patch.dict(os.environ, {'ANNOUNCEMENT_CHANNEL': '-100123'}):
        await game_database._update_expired_announcement(mock_context, game_data, "msg123")
        
        mock_context.bot.edit_message_text.assert_awaited_once()
        args = mock_context.bot.edit_message_text.call_args[1]
        assert args['chat_id'] == '-100123'
        assert "EXPIRED" in args['text']

def test_validate_game_data(game_database):
    valid_data = {
        "date": "01/01/2025",
        "end_time_24": "12:00",
        "sport": "Basketball"
    }
    assert game_database._validate_game_data(valid_data, "game123") is True
    
    invalid_data = {"date": "01/01/2025"}
    with patch('builtins.print') as mock_print:
        assert game_database._validate_game_data(invalid_data, "game123") is False
        mock_print.assert_called()

def test_cleanup_invalid_games(game_database):
    """Test cleaning up invalid games"""
    valid_game = MagicMock()
    valid_game.to_dict.return_value = {
        "sport": "Basketball",
        "date": "01/01/2025",
        "venue": "NUS",
        "skill": "Intermediate"
    }

    invalid_game = MagicMock()
    invalid_game.id = "invalid123"
    invalid_game.to_dict.return_value = {"sport": "Basketball"}
    invalid_game.reference = MagicMock()

    game_database.db.collection.return_value.stream.return_value = [valid_game, invalid_game]

    with patch('builtins.print') as mock_print:
        count = game_database.cleanup_invalid_games()

        assert count == 1
        invalid_game.reference.update.assert_called_once()
        assert "marked_invalid_at" in invalid_game.reference.update.call_args[0][0]
        # Update this line to match the full message:
        mock_print.assert_any_call("🗑️ Found invalid game invalid123 missing: ['date', 'venue', 'skill']")
        mock_print.assert_any_call('🧹 Marked 1 invalid games')

