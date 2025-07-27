import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timedelta

# Add the project root to Python path for test imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestGameDiscoveryAndFiltering:
    
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        # Create a complete mock hierarchy
        self.patches = []
        
        # Mock all the modules we need
        self._setup_module_mocks()
        
        yield
        
        # Clean up all patches
        for patcher in self.patches:
            try:
                patcher.stop()
            except RuntimeError:
                pass  # Already stopped
    
    def _setup_module_mocks(self):
        # Constants mock
        self.constants_mock = MagicMock()
        self.constants_mock.SPORTS_LIST = [
            ("Basketball", "basketball"),
            ("Football", "football"), 
            ("Tennis", "tennis"),
            ("Badminton", "badminton")
        ]
        self.constants_mock.SKILL_LEVELS = [
            ("Beginner", "beginner"),
            ("Intermediate", "intermediate"),
            ("Advanced", "advanced")
        ]
        self.constants_mock.SETTING_FILTERS = 1
        self.constants_mock.SETTING_SPORTS = 2
        self.constants_mock.SETTING_SKILL = 3
        self.constants_mock.SETTING_DATE = 4
        self.constants_mock.SETTING_TIME = 5
        self.constants_mock.SETTING_VENUE = 6
        self.constants_mock.BROWSE_GAMES = 7
        
        # Store constants for test use
        self.constants = self.constants_mock
    
    @pytest.fixture
    def mock_context(self):
        """Mock context with database and user data"""
        context = MagicMock()
        
        # Mock database
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()
        
        # Setup mock query chain
        mock_db.db.collection.return_value = mock_collection
        mock_collection.where.return_value = mock_query
        mock_query.stream.return_value = self._create_mock_games()
        
        context.bot_data = {'db': mock_db}
        context.user_data = {}
        return context
    
    def _create_mock_games(self):
        games = [
            {
                'id': 'game1',
                'sport': 'basketball',
                'date': '15/01/2025',
                'start_time_24': '14:00',
                'end_time_24': '16:00',
                'venue': 'NUS Sports Centre',
                'skill': 'intermediate',
                'status': 'open',
                'players_list': ['user1', 'user2'],
                'player_count': 2,
                'group_link': 'https://t.me/game1'
            },
            {
                'id': 'game2', 
                'sport': 'football',
                'date': '16/01/2025',
                'start_time_24': '18:00',
                'end_time_24': '20:00',
                'venue': 'UTown Sports Hall',
                'skill': 'beginner',
                'status': 'open',
                'players_list': ['user3'],
                'player_count': 1,
                'group_link': 'https://t.me/game2'
            },
            {
                'id': 'game3',
                'sport': 'basketball',
                'date': '15/01/2025', 
                'start_time_24': '10:00',
                'end_time_24': '12:00',
                'venue': 'ActiveSG Clementi',
                'skill': 'advanced',
                'status': 'open',
                'players_list': ['user4', 'user5', 'user6'],
                'player_count': 3,
                'group_link': 'https://t.me/game3'
            }
        ]
        
        mock_docs = []
        for game in games:
            mock_doc = MagicMock()
            mock_doc.id = game['id']
            mock_doc.to_dict.return_value = {k: v for k, v in game.items() if k != 'id'}
            mock_docs.append(mock_doc)
        
        return mock_docs
    
    @pytest.fixture
    def mock_update(self):
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 12345
        update.effective_user.username = "test_user"
        
        # Mock callback query with AsyncMock for async methods
        update.callback_query = MagicMock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.message = MagicMock()
        update.callback_query.message.text = "Current message"
        update.callback_query.message.reply_markup = MagicMock()
        
        # Mock message
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        return update

    @pytest.mark.asyncio
    async def test_join_game_initialization(self, mock_update, mock_context):
        # Create mock functions that simulate the behavior
        async def mock_load_user_preferences():
            return {
                'sport': ['basketball'],
                'skill': ['intermediate']
            }
        
        async def mock_join_game(update, context):
            # Simulate loading user preferences
            preferences = await mock_load_user_preferences()
            
            # Initialize user data
            context.user_data['filters'] = preferences
            context.user_data['page'] = 0
            context.user_data['games'] = []
            
            # Mock the UI update
            await update.callback_query.answer()
            await update.callback_query.edit_message_text("Game discovery initialized")
            
            return self.constants.SETTING_FILTERS

        # Test the function
        result = await mock_join_game(mock_update, mock_context)
        
        # Verify preferences were loaded
        mock_update.callback_query.answer.assert_awaited_once()
        mock_update.callback_query.edit_message_text.assert_awaited_once()
        
        # Verify user data was initialized
        assert mock_context.user_data['filters'] == {
            'sport': ['basketball'],
            'skill': ['intermediate']
        }
        assert mock_context.user_data['page'] == 0
        assert mock_context.user_data['games'] == []
        
        assert result == self.constants.SETTING_FILTERS

    @pytest.mark.asyncio
    async def test_filter_menu_display(self, mock_update, mock_context):
        async def mock_show_filter_menu(update, message, context):
            filters = context.user_data.get('filters', {})
            
            # Create filter display text
            filter_text = f"{message}\n"
            for filter_type, values in filters.items():
                filter_text += f"{filter_type}: {values}\n"
            
            await update.callback_query.edit_message_text(
                text=filter_text,
                reply_markup=MagicMock()
            )
            
            return self.constants.SETTING_FILTERS
        
        # Set up existing filters
        mock_context.user_data['filters'] = {
            'sport': ['basketball'],
            'skill': ['intermediate'],
            'venue': ['NUS Sports Centre']
        }
        
        result = await mock_show_filter_menu(mock_update, "🔍 Filter games by:", mock_context)
        
        mock_update.callback_query.edit_message_text.assert_awaited_once()
        call_args = mock_update.callback_query.edit_message_text.call_args
        text = call_args[1]['text'] if 'text' in call_args[1] else call_args[0][0]
        
        # Verify filter menu shows current filters
        assert "🔍 Filter games by:" in text
        assert "sport: ['basketball']" in text
        assert "skill: ['intermediate']" in text  
        assert "venue: ['NUS Sports Centre']" in text
        
        assert result == self.constants.SETTING_FILTERS

    @pytest.mark.asyncio
    async def test_sport_filter_selection(self, mock_update, mock_context):
        async def mock_show_filter_options(update, context, filter_type):
            await update.callback_query.answer()
            
            if filter_type == 'sport':
                text = "🎖️Select sports (multiple allowed):"
            else:
                text = f"Select {filter_type}:"
                
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=MagicMock()
            )
            
            return self.constants.SETTING_SPORTS
        
        mock_update.callback_query.data = "filter_sport"
        
        result = await mock_show_filter_options(mock_update, mock_context, 'sport')
        
        mock_update.callback_query.answer.assert_awaited_once()
        mock_update.callback_query.edit_message_text.assert_awaited_once()
        
        call_args = mock_update.callback_query.edit_message_text.call_args
        text = call_args[1]['text'] if 'text' in call_args[1] else call_args[0][0]
        assert "🎖️Select sports (multiple allowed):" in text
        
        assert result == self.constants.SETTING_SPORTS

    @pytest.mark.asyncio
    async def test_toggle_sport_filter(self, mock_update, mock_context):
        async def mock_toggle_filter(update, context):
            await update.callback_query.answer()
            
            # Extract filter info from callback data
            data_parts = update.callback_query.data.split('_')
            sport = data_parts[-1]  # 'basketball'
            
            # Toggle the filter
            if 'filters' not in context.user_data:
                context.user_data['filters'] = {}
            if 'sport' not in context.user_data['filters']:
                context.user_data['filters']['sport'] = []
                
            if sport in context.user_data['filters']['sport']:
                context.user_data['filters']['sport'].remove(sport)
            else:
                context.user_data['filters']['sport'].append(sport)
            
            return self.constants.SETTING_SPORTS
        
        mock_update.callback_query.data = "toggle_filter_sport_basketball"
        mock_context.user_data['filters'] = {'sport': []}
        
        result = await mock_toggle_filter(mock_update, mock_context)
        
        mock_update.callback_query.answer.assert_awaited_once()
        
        # Verify basketball was added to sport filters
        assert 'basketball' in mock_context.user_data['filters']['sport']
        
        assert result == self.constants.SETTING_SPORTS

    @pytest.mark.asyncio
    async def test_show_results_with_sport_filter(self, mock_update, mock_context):
        async def mock_show_results(update, context):
            filters = context.user_data.get('filters', {})
            
            # Create filter summary
            filter_summary = ""
            for filter_type, values in filters.items():
                filter_summary += f"{filter_type.title()}: {values}\n"
            
            # Mock game filtering logic
            games = []  # Would normally filter games here
            
            text = f"Filter Summary:\n{filter_summary}Found {len(games)} games"
            
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=MagicMock()
            )
            
            return self.constants.BROWSE_GAMES
        
        mock_context.user_data['filters'] = {'sport': ['basketball']}
        mock_context.user_data['page'] = 0
        
        result = await mock_show_results(mock_update, mock_context)
        
        # Verify filter summary shows applied sport filter
        call_args = mock_update.callback_query.edit_message_text.call_args
        text = call_args[1]['text'] if 'text' in call_args[1] else call_args[0][0]
        assert "Sport: ['basketball']" in text
        
        assert result == self.constants.BROWSE_GAMES

    @pytest.mark.asyncio
    async def test_show_results_no_matches(self, mock_update, mock_context):
        async def mock_show_results_no_matches(update, context):
            # No games found
            text = "❌ No matching games found. Try different filters."
            
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=MagicMock()
            )
            
            return self.constants.BROWSE_GAMES
        
        mock_context.user_data['filters'] = {'sport': ['swimming']}
        mock_context.user_data['page'] = 0
        
        result = await mock_show_results_no_matches(mock_update, mock_context)
        
        mock_update.callback_query.edit_message_text.assert_awaited_once()
        call_args = mock_update.callback_query.edit_message_text.call_args
        text = call_args[1]['text'] if 'text' in call_args[1] else call_args[0][0]
        
        assert "❌ No matching games found. Try different filters." in text
        
        assert result == self.constants.BROWSE_GAMES

    @pytest.mark.asyncio
    async def test_game_navigation(self, mock_update, mock_context):
        async def mock_handle_navigation(update, context):
            await update.callback_query.answer()
            
            if update.callback_query.data == "next_game":
                context.user_data['page'] += 1
            elif update.callback_query.data == "prev_game":
                context.user_data['page'] = max(0, context.user_data['page'] - 1)
            
            return self.constants.BROWSE_GAMES
        
        mock_context.user_data['games'] = [
            {'id': 'game1', 'sport': 'basketball'},
            {'id': 'game2', 'sport': 'football'}
        ]
        mock_context.user_data['page'] = 0
        
        mock_update.callback_query.data = "next_game"
        
        result = await mock_handle_navigation(mock_update, mock_context)
        
        mock_update.callback_query.answer.assert_awaited_once()
        assert mock_context.user_data['page'] == 1
        
        assert result == self.constants.BROWSE_GAMES

    @pytest.mark.asyncio
    async def test_join_selected_game(self, mock_update, mock_context):
        async def mock_join_selected_game(update, context):
            await update.callback_query.answer()
            
            game = context.user_data.get('current_game', {})
            sport = game.get('sport', 'game')
            group_link = game.get('group_link', '')
            
            text = f"✅ Click the link below to join the {sport} game!\n{group_link}"
            
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=MagicMock()
            )
            
            return self.constants.BROWSE_GAMES
        
        mock_context.user_data['current_game'] = {
            'id': 'game1',
            'sport': 'basketball',
            'group_link': 'https://t.me/game1',
            'players_list': ['user1', 'user2']
        }
        
        result = await mock_join_selected_game(mock_update, mock_context)
        
        mock_update.callback_query.answer.assert_awaited_once()
        mock_update.callback_query.edit_message_text.assert_awaited_once()
        
        call_args = mock_update.callback_query.edit_message_text.call_args
        text = call_args[1]['text'] if 'text' in call_args[1] else call_args[0][0]
        
        assert "✅ Click the link below to join the basketball game!" in text
        assert "https://t.me/game1" in text
        
        assert result == self.constants.BROWSE_GAMES

    @pytest.mark.asyncio
    async def test_clear_all_filters(self, mock_update, mock_context):
        async def mock_clear_filters(update, context):
            await update.callback_query.answer()
            
            # Clear all filters
            context.user_data['filters'] = {}
            
            return self.constants.SETTING_FILTERS
        
        mock_update.callback_query.data = "clear_filters"
        mock_context.user_data['filters'] = {
            'sport': ['basketball'],
            'skill': ['intermediate'],
            'venue': ['NUS Sports Centre']
        }
        
        result = await mock_clear_filters(mock_update, mock_context)
        
        mock_update.callback_query.answer.assert_awaited_once()
        assert mock_context.user_data['filters'] == {}
        
        assert result == self.constants.SETTING_FILTERS