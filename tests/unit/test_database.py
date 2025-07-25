import pytest
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock
from freezegun import freeze_time

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Mock all utils modules before any imports
utils_mock = MagicMock()
utils_mock.is_game_expired = MagicMock(return_value=False)
sys.modules['utils'] = utils_mock
sys.modules['utils.datetime_helper'] = MagicMock()
sys.modules['utils.groupid_helper'] = MagicMock()
sys.modules['utils.validation_helper'] = MagicMock()
sys.modules['utils.constants'] = MagicMock()
sys.modules['bot.services.telethon_service'] = MagicMock()

# Mock firebase modules
firebase_admin_mock = MagicMock()
firebase_admin_mock._apps = []
credentials_mock = MagicMock()
firestore_mock = MagicMock()
sys.modules['firebase_admin'] = firebase_admin_mock
sys.modules['firebase_admin.credentials'] = credentials_mock
sys.modules['firebase_admin.firestore'] = firestore_mock

from bot.services.database import GameDatabase

@pytest.fixture
def mock_firestore():
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_document = MagicMock()
    
    mock_client.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_document
    
    return mock_client, mock_collection, mock_document

@pytest.fixture
def database(mock_firestore):
    mock_client, mock_collection, mock_document = mock_firestore
    
    with patch('firebase_admin.initialize_app'), \
         patch('firebase_admin.credentials.Certificate'), \
         patch('firebase_admin.firestore.client', return_value=mock_client), \
         patch.dict('os.environ', {'FIREBASE_CREDENTIALS': 'fake_credentials.json'}):
        
        db = GameDatabase()
        db.mock_client = mock_client
        db.mock_collection = mock_collection
        db.mock_document = mock_document
        return db

class TestGameDatabase:
    
    def test_save_game(self, database):
        game_data = {
            "sport": "Basketball",
            "date": "25/12/2025",
            "venue": "NUS Court",
            "host": "user123"
        }
        
        # Mock document reference
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "game123"
        database.mock_collection.document.return_value = mock_doc_ref
        
        # Call the method
        result = database.save_game(game_data.copy())
        
        # Assertions
        assert result == "game123"
        database.mock_client.collection.assert_called_with("game")
        mock_doc_ref.set.assert_called_once()
        
        # Check that created_at was added
        call_args = mock_doc_ref.set.call_args[0][0]
        assert "created_at" in call_args
        assert call_args["sport"] == "Basketball"

    def test_update_game(self, database):
        game_id = "game123"
        update_data = {"status": "closed"}
        
        mock_doc_ref = MagicMock()
        database.mock_collection.document.return_value = mock_doc_ref
        
        # Call the method
        database.update_game(game_id, update_data)
        
        # Assertions
        database.mock_client.collection.assert_called_with("game")
        database.mock_collection.document.assert_called_with(game_id)
        mock_doc_ref.update.assert_called_with(update_data)


    @pytest.mark.asyncio
    async def test_get_hosted_games(self, database):
        host_id = "user123"
        mock_context = MagicMock()
        
        # Mock query results
        mock_game_doc = MagicMock()
        mock_game_doc.id = "game123"
        mock_game_doc.to_dict.return_value = {
            "sport": "Basketball",
            "host": host_id,
            "status": "open"
        }
        
        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_game_doc]
        
        # Chain the query methods
        database.mock_collection.where.return_value.where.return_value = mock_query
        
        # Mock close_expired_games to do nothing
        with patch.object(database, 'close_expired_games', new_callable=AsyncMock):
            result = await database.get_hosted_games(mock_context, host_id)
        
        # Assertions
        assert len(result) == 1
        assert result[0]["id"] == "game123"
        assert result[0]["sport"] == "Basketball"
        assert result[0]["host"] == host_id

    @pytest.mark.asyncio
    async def test_get_all_open_games(self, database):
        # Mock query results
        mock_game_doc = MagicMock()
        mock_game_doc.id = "game123"
        mock_game_doc.to_dict.return_value = {
            "sport": "Football",
            "status": "open"
        }
        
        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_game_doc]
        database.mock_collection.where.return_value = mock_query
        
        result = await database.get_all_open_games()
        
        # Assertions
        assert len(result) == 1
        assert result[0]["id"] == "game123"
        assert result[0]["sport"] == "Football"


    def test_check_game_expired(self, database):
        game_data = {
            "date": "25/12/2025",
            "end_time_24": "16:00"
        }
        
        # Mock the is_game_expired function
        utils_mock.is_game_expired.return_value = True
        
        result = database.check_game_expired(game_data)
        
        assert result is True
        utils_mock.is_game_expired.assert_called_with("25/12/2025", "16:00")


    def test_cancel_game(self, database):
        game_id = "game123"
        
        # Mock document
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "announcement_msg_id": "msg123",
            "sport": "Basketball"
        }
        mock_doc_ref.get.return_value = mock_doc
        
        database.mock_collection.document.return_value = mock_doc_ref
        
        result = database.cancel_game(game_id)
        
        # Assertions
        assert result == "msg123"
        mock_doc_ref.update.assert_called_once()
        call_args = mock_doc_ref.update.call_args[0][0]
        assert call_args["status"] == "cancelled"
        assert "cancelled_at" in call_args

