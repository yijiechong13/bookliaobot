from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils import *
from config import *

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Use a service account.
cred = credentials.Certificate('path/to/serviceAccount.json')
app = firebase_admin.initialize_app(cred)
db = firestore.client()

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['filters'] = {}
    context.user_data['page'] = 0
    return await show_filter_menu (update, "🔍 Filter games by:")

async def show_filter_menu(update: Update, text: str) -> int:
    buttons = [
        ["Sports", "filter_sport"],
        ["Time", "filter_time"],
        ["Venue", "filter_venue"],
        ["Skill", "filter_skill"],
        ["Show Restults", "show_results"],
    ]
    reply_markup = InlineKeyboardButton(
        [[InlineKeyboardButton(text, callback_data=data)] for text, data in buttons]
    )

    if hasattr(update, 'callback_query'):
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    return SPORT

async def handle_filter_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, filter_type: str) -> int:
    query = update.callback_query
    await query.answer()

    handlers = {
        'sport': (await show_sport_filter(update)),
        'time': (await query.edit_message_text("What time is the game? (e.g., 'Today 6pm-8pm' or 'Saturday 2pm-4pm') or /skip"), TIME),
        'venue': (await query.edit_message_text("Enter venue or /skip"), VENUE),
        'skill': (await show_skill_filter(update)),
        'results': (await show_results(update, context), ConversationHandler.END),
        'clear': (context.user_data['filters'].clear(), await show_filter_menu(update, "Filters cleared!"))
    }

    return handlers.get(filter_type.split('_')[1], await show_filter_menu(update, "Select filter:"))

async def show_sport_filter(update: Update) -> int:
    buttons = [[sport, f"sport_{sport}"] for sport in sports] + [["Skip", "skip_sport"]]
    await update.callback_query.edit_message_text(
        "Select sport:",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text, callback_data=data)] for text, data in buttons]
        
        )
    )
    return SPORT

async def show_skill_filter(update:Update) -> int:
    buttons = [[level, f"sport_{level}"] for level in SKILL_LEVEL] + [["Skip", "skip_skill"]]
    await update.callback_query.edit_message_text(
        "Select skill level:",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text, callback_data=data)] for text, data in buttons]
        )
    )
    return SKILL


async def save_filter(update: Update, context: ContextTypes.DEFAULT_TYPE, filter_key: str, filter_value: str) -> int:
    if not filter_value.startswith('skip'):
        context.user_date['filters'][filter_key] = filter_value.split('_')[1]
    return await show_filter_menu(update, f"✅ {filter_key.capitalize()} filter applied")

async def save_text_filter(update: Update, context: ContextTypes.DEFAULT_TYPE, filter_key: str, filter_value: str) -> int:
    if update.message.text.lower() != '/skip':
        context.user_data['filters'][filter_key] = update.message.text
    return await show_filter_menu(update, f"✅ {filter_key.capitalize()} filter applied")



async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    filters = context.user_data.get('filters', {})
    page = context.user_data.get('page', 0)

    games_ref = db.collection("game")
    if 'sport' in context.user_data['filters']:
        games_ref = games_ref.where('sport', '==', context.user_data['filters']['sport'])
    if 'skill' in context.user_data['filters']:
        games_ref = games_ref.where('skill', '==', context.user_data['filters']['skill'])
    
    games = [doc.to_dict() for doc in games_ref.stream()]
    context.user_data['games'] = games

    if not games:
        await query.edit_message_text("❌ No matching games found. Try different filters.")
    page = context.user_data.get('page', 0) % len(games)
    game = games[page]
    context.user_data['current_game'] = game

    message = (
        "Please confirm game details and join the Telegram Group Chat"
        f"🏟️ Game Joined:\n\n"
        f"🏀 Sport: {game.get('sport', 'Game')}\n"
        f"🕒 Time: {game.get('time', 'N/A')}\n"
        f"📍 Venue: {game.get('venue', 'N/A')}\n"
        f"📊 Skill: {game.get('skill', 'Any').title()}\n"
        f"👥 Players: {game.get('players', 1)}/{game.get('max_players',10)}players\n\n"
        f"🔗 {game.get('group_link', 'No link available')}"
    )

    buttons = []
    if len(games) > 1:
        buttons.extend([
            InlineKeyboardButton("⬅️ Prev", callback_data="prev_game"),
            InlineKeyboardButton("➡️ Next", callback_data="next_game")
        ])
    buttons.append(InlineKeyboardButton("✅ Join", callback_data="join_game"))

    await query.edit_message_text(
        message, reply_markup=InlineKeyboardMarkup([buttons])
    )

    return SHOWING_RESULTS

async def handle_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE)-> int:
    query = update.callback_query
    await query.answer()

    if query.data == "next_game":
        context.user_data['page'] = context.user_data.get('page', 0) + 1
    elif query.data == "prev_game":
        context.user_data['page'] = max(0, context.user_data.get('page', 0) - 1)
    
    return await show_results(update, context)

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    game = context.user_data.get('current_game', {})

    await query.edit_message_text(
        f"✅ You've joined the {game.get('sport')} game! \m"
        f"Group: {game.get('group_link', 'Contact organizer')}",
        reply_markup=InlineKeyboardButton([
            [InlineKeyboardButton("Back to Results", callback_data="back_to_results")]
        ])
    )
    return ConversationHandler.END
