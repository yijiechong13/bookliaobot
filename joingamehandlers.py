from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler, 
                          MessageHandler, filters,
                          ContextTypes, ConversationHandler)
from utils import *
from config import *

from dotenv import load_dotenv
import os
load_dotenv()
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")
from firebase_init import *


async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    context.user_data.update({
        'filters' : {},
        'page' : 0,
        'games' : []
    })
    return await show_filter_menu (update, "🔍 Filter games by:")

async def show_filter_menu(update: Update, text: str) -> int:
    try:
        buttons = [
            ["⚽ Sports", "filter_sport"],
            ["🕒 Time", "filter_time"],
            ["📍 Venue", "filter_venue"],
            ["📊 Skill", "filter_skill"],
            ["🔍 Show Restults", "show_results"],
        ]
        # Create keyboard with one button per row
        keyboard = [
            [InlineKeyboardButton(text, callback_data=data)]
            for text, data in buttons
        ]
        
        # Add Back button as a separate row
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_filters")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=str(text),
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text=str(text),
                reply_markup=reply_markup
            )
        
        return SETTING_SPORTS
    except Exception as e:
        print(f"Error in show_filter_menu: {str(e)}")
        if update.callback_query:
            await update.callback_query.message.reply_text("⚠️ Menu error. Please try again.")
        return ConversationHandler.END


async def handle_filter_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, filter_type: str) -> int:
    query = update.callback_query
    await query.answer()
    print(f"Callback data received: {query.data}")  # Debug log
    
    filter_type = filter_type.split('_')[1]
    
    if filter_type == 'sport':
        return await filter_sport(update,context)
    elif filter_type == 'time':
        await query.edit_message_text("What time is the game? (e.g., 'Today 6pm-8pm' or 'Saturday 2pm-4pm'):")
        return TIME
    elif filter_type == 'venue':
        await update.message.reply_text("Enter venue/location:")
        return VENUE
    elif filter_type == 'skill':
        return await filter_skill(update)
    elif filter_type == 'results':
        return await show_results(update, context)
    else:
        return await show_filter_menu(update,"Select a filter:")


async def filter_sport(update: Update,context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        sports = {doc.to_dict().get("sport") for doc in db.collection("game").stream()}
        sports.discard(None)

        if not sports:
            await query.edit_message_text("No sports available.")
            return SETTING_SPORTS
        
        filters = context.user_data.setdefault('filters', {})
        selected = filters.get('sport', [])
        selected = [selected] if selected and not isinstance(selected, list) else selected or []

        keyboard = [
            [InlineKeyboardButton(
                f"{'✅ ' if sport in selected else '⚪ '} {sport}",
                callback_data=f"toggle_sport_{sport}"
            )]
            for sport in sorted(sports)
        ]
        # Add action buttons
        keyboard += [
            [
                InlineKeyboardButton("🔙 Back", callback_data="back_to_filters"),
                InlineKeyboardButton("Apply Filters", callback_data="apply_sport_filters")
            ]
        ]

        await query.edit_message_text(
            "⚽ Select sports (click to toggle):\n"
            "✅ = selected | ⚪ = available",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SETTING_SPORTS
    except Exception as e:
        print(f"Firebase error: {e}")
        await query.edit_message_text("🚨 Failed to fetch sports. Try again later.")
        return SETTING_SPORTS


async def toggle_sport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    sport = query.data.split('_')[-1]
    filters = context.user_data.setdefault('filters', {})
    selected = filters.get('sport', [])
    
    # Ensure we're working with a list
    selected = selected if isinstance(selected, list) else [selected] if selected else []
    
    # Toggle selection
    filters['sport'] = [s for s in selected if s != sport] if sport in selected else selected + [sport]
    
    return await filter_sport(update, context)

async def apply_sport_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Clean the sport filter data
    filters = context.user_data.setdefault('filters', {})
    
    # Handle case where no sports are selected
    if not filters.get('sport'):
        await query.edit_message_text("ℹ️ No sports selected - showing all available games")
        filters['sport'] = []  # Empty list shows all sports
    
    # Reset pagination
    context.user_data['page'] = 0
    
    # Proceed to show results
    return await show_results(update, context)

async def save_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    filter_key, filter_value = data.split('_')
    context.user_data['filters'][filter_key] = filter_value
    return await show_filter_menu(update, f"✅ {filter_key.capitalize()} filter applied")

async def save_text_filter(update: Update, context: ContextTypes.DEFAULT_TYPE, filter_key: str, filter_value: str) -> int:
    if filter_value.lower() != '/skip':
        context.user_data['filters'][filter_key] = filter_value
    return await show_filter_menu(update, f"✅ {filter_key.capitalize()} filter applied")

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    filters = context.user_data.get('filters', {})
    page = context.user_data.get('page', 0)
    games_ref = db.collection("game")

    if sports := filters.get('sport'):
        sports = [sports] if isinstance(sports, str) else sports
        games_ref = games_ref.where('sport', 'in', sports)
    if 'skill' in context.user_data['filters']:
        games_ref = games_ref.where('skill', '==', context.user_data['filters']['skill'])
    
    games = [doc.to_dict() for doc in games_ref.stream()]
    context.user_data['games'] = games

    if 'time' in filters:
        games = [g for g in games if filters['time'].lower() in g.get('time', '').lower()]
    if 'venue' in filters:
        games = [g for g in games if filters['venue'].lower() in g.get('venue', '').lower()]
    
    if not games:
        await query.edit_message_text("❌ No matching games found. Try different filters.")
        return SETTING_SPORTS
    
    page %= len(games)
    context.user_data['page'] = page
    game = games[page]
    context.user_data['current_game'] = game

    filters_summary = "\n".join(
        [f"• {k.capitalize()}: {v}" for k, v in filters.items()]
    ) or "None"

    selected_sports = filters.get('sport', [])
    selected_sports = ', '.join(selected_sports) if isinstance(selected_sports, list) else selected_sports

    game_info = (
        f"🎯 <b>Matching Game #{page+1}</b>\n\n"
        f"🏅 <b>Sport:</b> {game.get('sport', 'N/A').title()}\n"
        f"🕒 <b>Time:</b> {game.get('time', 'N/A')}\n"
        f"📍 <b>Venue:</b> {game.get('venue', 'N/A')}\n"
        f"📊 <b>Skill:</b> {game.get('skill', 'Any').title()}\n"
        f"👥 <b>Players:</b> {len(game.get('players', []))} / {game.get('max_players',10)} "
        f"{'(🏟️ FULL)' if len(game.get('players', [])) >= game.get('max_players', 10) else '✅ OPEN'}\n\n"
        f"🔗 <b>Group:</b> {game.get('group_link', 'Not  available')}\n\n"
        f"🔎 <b>Filters applied:</b>{filters_summary}"
    )

    buttons = []
    if len(games) > 1:
        buttons = [
            InlineKeyboardButton("⬅️ Prev", callback_data="prev_game"),
            InlineKeyboardButton(f"{page+1}/{len(games)}", callback_data="page_info"),
            InlineKeyboardButton("➡️ Next", callback_data="next_game")
        ]
    action = [
        InlineKeyboardButton("✅ Join", callback_data="join_selected_game"),
        InlineKeyboardButton("🔙 Back to Filters", callback_data="back_to_filters"),
    ]


    reply_markup= InlineKeyboardMarkup([buttons, action] if buttons else [action])

    await query.edit_message_text(
        game_info,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

    return BROWSE_GAMES

async def handle_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE)-> int:
    query = update.callback_query
    await query.answer()

    if query.data == "next_game":
        context.user_data['page'] = context.user_data.get('page', 0) + 1
    elif query.data == "prev_game":
        context.user_data['page'] = max(0, context.user_data.get('page', 0) - 1)
    
    return await show_results(update, context)

async def join_selected_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    game = context.user_data.get('current_game', {})

    if not game.get('id'):
        await query.edit_message_text("Invalid game selected")
        return BROWSE_GAMES
    
    if update._effective_user.id in game.get('players_list', []):
        await query.edit_message_text("You've already joined this game")
        return BROWSE_GAMES
    
    if len(game.get('players', [])) >= game.get('max_players', 10):
        await query.edit_message_text(" This game is already full")
        return BROWSE_GAMES

    game_ref = db.collection("game").document(game['id'])
    game_ref.update({
        'players': firestore.Increment(1),
        'players_list': firestore.ArrayUnion([update.effective_user.id])
    })

    await query.edit_message_text(
        f"✅ You've joined the {game.get('sport')} game! \n"
        f"Group: {game.get('group_link')}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Back to Filters", callback_data="back_to_filters")]
        ])
    )
    return ConversationHandler.END
