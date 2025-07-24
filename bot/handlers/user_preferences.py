from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from firebase_admin import firestore
import datetime
import logging

async def load_user_preferences(user_id: str, db) -> dict:
    try:
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
    except Exception as e:
        logging.error(f"Error loading user preferences: {str(e)}")
        return {}

async def save_user_preferences(user_id: str, preferences: dict, db) -> bool:
    try:
        user_pref_ref = db.db.collection("user_preference").document(user_id)
        
        pref_data = {
            'sport': preferences.get('sport'),
            'skill': preferences.get('skill'),
            'venue': preferences.get('venue'),
            'updated_at': datetime.datetime.now()
        }
        
        # Only save non-empty preferences
        pref_data = {k: v for k, v in pref_data.items() if v and k != 'updated_at'}
        if pref_data:
            pref_data['updated_at'] = datetime.datetime.now()
            user_pref_ref.set(pref_data, merge=True)
            return True
        
        return False
    except Exception as e:
        logging.error(f"Error saving user preferences: {str(e)}")
        return False

async def clear_user_preferences(user_id: str, db) -> bool:
    try:
        user_pref_ref = db.db.collection("user_preference").document(user_id)
        user_pref_ref.delete()
        return True
    except Exception as e:
        logging.error(f"Error clearing user preferences: {str(e)}")
        return False

async def clear_specific_preference(user_id: str, preference_type: str, db) -> bool:
    try:
        user_pref_ref = db.db.collection("user_preference").document(user_id)
        
        firestore_field = {
            'sport': 'sport',
            'skill': 'skill',
            'venue': 'venue'
        }.get(preference_type)
        
        if firestore_field:
            doc = user_pref_ref.get()
            if doc.exists:
                user_pref_ref.update({
                    firestore_field: firestore.DELETE_FIELD,
                    'updated_at': datetime.datetime.now()
                })
                return True
        
        return False
    except Exception as e:
        logging.error(f"Error clearing specific preference: {str(e)}")
        return False

async def save_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from .game_filters import show_filter_menu
    
    query = update.callback_query
    await query.answer()

    try:
        db = context.bot_data['db']
        filters = context.user_data.get('filters', {})
        user_id = str(update.effective_user.id)
        
        success = await save_user_preferences(user_id, filters, db)
        
        if success:
            return await show_filter_menu(update, "✅ Preferences saved successfully! Filter games by:", context)
        else:
            return await show_filter_menu(update, "ℹ️ No preferences to save. Filter games by:", context)
            
    except Exception as e:
        logging.error(f"Error in save_preferences handler: {str(e)}")
        await query.edit_message_text("❌ Failed to save preferences. Please try again.")
        return await show_filter_menu(update, "🔍 Filter games by:", context)

async def clear_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from .game_filters import show_filter_menu
    
    query = update.callback_query
    await query.answer()

    try:
        db = context.bot_data['db']
        parts = query.data.split('_')
        user_id = str(update.effective_user.id)

        if len(parts) == 2:
            # Clear all filters
            context.user_data['filters'] = {}
            await clear_user_preferences(user_id, db)
            await query.edit_message_text("✅ All filters have been cleared.")
            return await show_filter_menu(update, "🔍 Filter games by:", context)
        
        if len(parts) < 3:
            raise ValueError("Invalid callback data format")
        
        filter_type = parts[1]
        
        # Clear from context
        if filter_type in context.user_data.get('filters', {}):
            context.user_data['filters'][filter_type] = []
        
        # Clear from Firebase
        await clear_specific_preference(user_id, filter_type, db)

        # Import and call the appropriate filter function
        from .game_filters import filter_sport, filter_skill, filter_date, filter_time, filter_venue
        
        filter_handlers = {
            'sport': filter_sport,
            'skill': filter_skill,
            'date': filter_date,
            'time': filter_time,
            'venue': filter_venue,
        }
        
        filter_func = filter_handlers.get(filter_type)
        if filter_func:
            return await filter_func(update, context)
        
        raise ValueError(f"Unknown filter type: {filter_type}")
        
    except Exception as e:
        logging.error(f"Clear filter error: {str(e)}")
        await query.edit_message_text("❌ Could not clear filters. Please try again later.")
        return await show_filter_menu(update, "🔍 Filters cleared! Filter games by:", context)