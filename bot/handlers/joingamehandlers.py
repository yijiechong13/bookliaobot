from telegram import Update
from telegram.ext import ContextTypes
from utils.constants import *
from .user_preferences import load_user_preferences
from .game_filters import show_filter_menu


async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = context.bot_data['db']
    if db is None:
        db = context.bot_data['db']  

    query = update.callback_query
    await query.answer()
    context.user_data.clear()

    user_id = str(update.effective_user.id)
    
    filters = await load_user_preferences(user_id, db)

    context.user_data.update({
        'filters': filters,
        'page': 0,
        'games': []
    })
    
    return await show_filter_menu(update, "🔍 Filter games by:", context)

async def back_to_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await show_filter_menu(update, "🔍 Filter games by:", context)

async def handle_filter_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from .game_filters import show_filter_options
    
    query = update.callback_query
    await query.answer()
    
    filter_type = query.data.split('_')[1]
    return await show_filter_options(update, context, filter_type)

from .user_preferences import save_preferences, clear_filters
from .game_filters import (
    filter_sport, filter_skill, filter_date, filter_time, filter_venue,
    toggle_filter, apply_filters, show_results, handle_navigation, join_selected_game
)