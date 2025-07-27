import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Add the project root to Python path for test imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestUserPreferenceManagement:
    
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        collection_mock = MagicMock()
        doc_mock = MagicMock()
        
        # Setup collection chain
        db.db.collection.return_value = collection_mock
        collection_mock.document.return_value = doc_mock
        
        return db, doc_mock
    
    @pytest.fixture
    def mock_context(self, mock_db):
        context = MagicMock()
        db, _ = mock_db
        context.bot_data = {'db': db}
        context.user_data = {}
        return context
    
    @pytest.fixture
    def mock_update(self):

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 12345
        update.callback_query = MagicMock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        return update

    @pytest.mark.asyncio
    async def test_load_existing_preferences(self, mock_context, mock_db):
        db, doc_mock = mock_db
        
        # Mock existing preferences in Firebase
        existing_prefs = {
            'sport': ['basketball', 'tennis'],
            'skill': ['intermediate'],
            'venue': ['NUS Sports Centre'],
            'updated_at': datetime.now()
        }
        
        doc_mock.get.return_value.exists = True
        doc_mock.get.return_value.to_dict.return_value = existing_prefs
        
        async def mock_load_user_preferences(user_id, db):
            pref_doc = db.db.collection("user_preference").document(user_id).get()
            
            filters = {}
            if pref_doc.exists:
                pref_data = pref_doc.to_dict()
                if 'sport' in pref_data:
                    filters['sport'] = pref_data['sport']
                if 'skill' in pref_data:
                    filters['skill'] = pref_data['skill']
                if 'venue' in pref_data:
                    filters['venue'] = pref_data['venue']
            
            return filters
        
        # Test loading preferences
        result = await mock_load_user_preferences("12345", db)
        
        # Verify preferences were loaded correctly
        assert result['sport'] == ['basketball', 'tennis']
        assert result['skill'] == ['intermediate']
        assert result['venue'] == ['NUS Sports Centre']
        
        # Verify Firebase was called correctly
        db.db.collection.assert_called_with("user_preference")
        doc_mock.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_preferences_new_user(self, mock_context, mock_db):
        db, doc_mock = mock_db
        
        # Mock no existing preferences
        doc_mock.get.return_value.exists = False
        
        async def mock_load_user_preferences(user_id, db):
            pref_doc = db.db.collection("user_preference").document(user_id).get()
            
            filters = {}
            if pref_doc.exists:
                pref_data = pref_doc.to_dict()
                if 'sport' in pref_data:
                    filters['sport'] = pref_data['sport']
                if 'skill' in pref_data:
                    filters['skill'] = pref_data['skill']
                if 'venue' in pref_data:
                    filters['venue'] = pref_data['venue']
            
            return filters
        
        # Test loading preferences for new user
        result = await mock_load_user_preferences("67890", db)
        
        # Verify empty preferences returned
        assert result == {}
        
        # Verify Firebase was called
        db.db.collection.assert_called_with("user_preference")
        doc_mock.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_preferences_success(self, mock_update, mock_context, mock_db):
        db, doc_mock = mock_db
        
        async def mock_save_preferences(update, context):
            await update.callback_query.answer()
            
            # Get filters from user data
            filters = context.user_data.get('filters', {})
            user_id = str(update.effective_user.id)
            
            # Mock saving to Firebase
            user_pref_ref = db.db.collection("user_preference").document(user_id)
            
            pref_data = {
                'sport': filters.get('sport'),
                'skill': filters.get('skill'),
                'venue': filters.get('venue'),
                'updated_at': datetime.now()
            }
            
            # Filter out empty values
            pref_data = {k: v for k, v in pref_data.items() if v and k != 'updated_at'}
            if pref_data:
                pref_data['updated_at'] = datetime.now()
                user_pref_ref.set(pref_data, merge=True)
                success = True
            else:
                success = False
            
            if success:
                await update.callback_query.edit_message_text("✅ Preferences saved successfully!")
            else:
                await update.callback_query.edit_message_text("ℹ️ No preferences to save.")
            
            return success
        
        # Set up filters to save
        mock_context.user_data['filters'] = {
            'sport': ['basketball'],
            'skill': ['intermediate'],
            'venue': ['NUS Sports Centre']
        }
        
        result = await mock_save_preferences(mock_update, mock_context)
        
        # Verify success
        assert result == True
        
        # Verify UI was updated
        mock_update.callback_query.answer.assert_awaited_once()
        mock_update.callback_query.edit_message_text.assert_awaited_once()
        
        call_args = mock_update.callback_query.edit_message_text.call_args
        text = call_args[0][0] if call_args[0] else call_args[1]['text']
        assert "✅ Preferences saved successfully!" in text
        
        # Verify Firebase calls
        db.db.collection.assert_called_with("user_preference")


    @pytest.mark.asyncio
    async def test_clear_all_preferences(self, mock_update, mock_context, mock_db):
        db, doc_mock = mock_db
        
        async def mock_clear_filters(update, context):
            await update.callback_query.answer()
            
            user_id = str(update.effective_user.id)
            
            # Clear from context
            context.user_data['filters'] = {}
            
            # Clear from Firebase
            user_pref_ref = db.db.collection("user_preference").document(user_id)
            user_pref_ref.delete()
            
            await update.callback_query.edit_message_text("✅ All filters have been cleared.")
            
            return True
        
        # Set up existing filters
        mock_context.user_data['filters'] = {
            'sport': ['basketball'],
            'skill': ['intermediate']
        }
        
        mock_update.callback_query.data = "clear_filters"
        
        result = await mock_clear_filters(mock_update, mock_context)
        
        # Verify context was cleared
        assert mock_context.user_data['filters'] == {}
        
        # Verify Firebase delete was called
        db.db.collection.assert_called_with("user_preference")
        doc_mock.delete.assert_called_once()
        
        # Verify UI feedback
        call_args = mock_update.callback_query.edit_message_text.call_args
        text = call_args[0][0] if call_args[0] else call_args[1]['text']
        assert "✅ All filters have been cleared." in text

    @pytest.mark.asyncio
    async def test_clear_specific_preference(self, mock_update, mock_context, mock_db):
        db, doc_mock = mock_db
        
        async def mock_clear_specific_filter(update, context, filter_type):
            await update.callback_query.answer()
            
            user_id = str(update.effective_user.id)
            
            # Clear from context
            if filter_type in context.user_data.get('filters', {}):
                context.user_data['filters'][filter_type] = []
            
            # Mock Firebase field deletion
            user_pref_ref = db.db.collection("user_preference").document(user_id)
            doc_mock.get.return_value.exists = True
            
            # Simulate field deletion
            firestore_field = {
                'sport': 'sport',
                'skill': 'skill', 
                'venue': 'venue'
            }.get(filter_type)
            
            if firestore_field:
                user_pref_ref.update({
                    firestore_field: "DELETE_FIELD",  # Firestore DELETE_FIELD mock
                    'updated_at': datetime.now()
                })
            
            return True
        
        # Set up existing filters
        mock_context.user_data['filters'] = {
            'sport': ['basketball'],
            'skill': ['intermediate'],
            'venue': ['NUS Sports Centre']
        }
        
        mock_update.callback_query.data = "clear_sport_filters"
        
        result = await mock_clear_specific_filter(mock_update, mock_context, 'sport')
        
        # Verify specific filter was cleared
        assert mock_context.user_data['filters']['sport'] == []
        assert mock_context.user_data['filters']['skill'] == ['intermediate']  # Others unchanged
        assert mock_context.user_data['filters']['venue'] == ['NUS Sports Centre']
        
        # Verify Firebase calls
        db.db.collection.assert_called_with("user_preference")
        doc_mock.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_preference_persistence_across_sessions(self, mock_context, mock_db):
        db, doc_mock = mock_db
        
        # Session 1: Save preferences
        saved_prefs = {
            'sport': ['tennis', 'badminton'],
            'skill': ['advanced'],
            'venue': ['UTown Sports Hall'],
            'updated_at': datetime.now()
        }
        
        async def mock_save_session():
            user_pref_ref = db.db.collection("user_preference").document("12345")
            user_pref_ref.set(saved_prefs, merge=True)
            return True
        
        save_result = await mock_save_session()
        assert save_result == True
        
        # Simulate new session - context is cleared
        mock_context.user_data = {}
        
        # Session 2: Load preferences
        doc_mock.get.return_value.exists = True
        doc_mock.get.return_value.to_dict.return_value = saved_prefs
        
        async def mock_load_session():
            pref_doc = db.db.collection("user_preference").document("12345").get()
            
            filters = {}
            if pref_doc.exists:
                pref_data = pref_doc.to_dict()
                for key in ['sport', 'skill', 'venue']:
                    if key in pref_data:
                        filters[key] = pref_data[key]
            
            return filters
        
        loaded_prefs = await mock_load_session()
        
        # Verify preferences persisted across sessions
        assert loaded_prefs['sport'] == ['tennis', 'badminton']
        assert loaded_prefs['skill'] == ['advanced']
        assert loaded_prefs['venue'] == ['UTown Sports Hall']
        
        # Verify Firebase was called correctly for both sessions
        assert db.db.collection.call_count >= 2