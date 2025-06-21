from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler, 
                          MessageHandler, filters,
                          ContextTypes, ConversationHandler)
from host.utils import *
from config import *
from typing import Optional

from dotenv import load_dotenv
import os
import logging
import telegram
load_dotenv()
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")
from member.firebase_init import *


async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    context.user_data.update({
        'filters' : {},
        'page' : 0,
        'games' : []
    })
    return await show_filter_menu (update, "🔍 Filter games by:", context)

async def show_filter_menu(update: Update, text: str, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        filters = context.user_data.get('filters', {})

        buttons = [
            [f"⚽ Sports {'✅' if 'sport' in filters else ''}", "filter_sport"],
            [f"📅 Date {'✅' if 'date' in filters else ''}", "filter_date"],
            [f"🕒 Time {'✅' if 'time' in filters else ''}", "filter_time"],
            [f"📍 Venue {'✅' if 'venue' in filters else ''}", "filter_venue"],
            [f"📊 Skill {'✅' if 'skill' in filters else ''}", "filter_skill"],
            ["🔍 Show Results", "show_results"],
        ]

        keyboard = [
            [InlineKeyboardButton(text, callback_data=data)]
            for text, data in buttons
        ]


        keyboard.append([
            InlineKeyboardButton("🧹 Clear Filters", callback_data="clear_filters"),
            InlineKeyboardButton("🔙 Back", callback_data="main_menu"),
            ])
        
        #Filters summary
        active_filters = "\n".join([f"• {k}: {v}" for k,v in filters.items()]) or "None"
        message = f"{text} \n\nCurrent filters:\n{active_filters}"
        
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=message,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text=message,
                reply_markup=reply_markup
            )
        
        return SETTING_FILTERS
    except Exception as e:
        print(f"Error in show_filter_menu: {str(e)}")
        if update.callback_query:
            await update.callback_query.message.reply_text("⚠️ Menu error. Please try again.")
        return ConversationHandler.END

async def clear_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    try:
        parts = query.data.split('_')
        if len(parts) == 2:
            context.user_data['filters'] = {}
            await query.edit_message_text("✅ All filters have been cleared.")
            return await show_filter_menu(update, "🔍 Filter games by:", context)
        
        if len(parts) < 3:
            raise ValueError("Invalid callback data format")
        
        filter_type = parts[1]

        if filter_type in context.user_data.get('filters', {}):
            context.user_data['filters'][filter_type] = []

        filter_func = globals().get(f"filter_{filter_type}")
        if filter_func:
            return await filter_func(update, context)
        
        raise ValueError(f"Unknown filter type: {filter_type}")
        
    except Exception as e:
        logging.error(f"Clear filter error : {str(e)}")
        await query.edit_message_text("Could not clear filters. Please try again later.")
        return await show_filter_menu(update, "🔍 Filters cleared! Filter games by:", context)

async def back_to_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await show_filter_menu (update, "🔍 Filter games by:", context)

async def handle_filter_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    filter_type = query.data.split('_')[1]
    return await show_filter_options(update, context, filter_type)


async def show_filter_options(update: Update,context: ContextTypes.DEFAULT_TYPE, filter_type:str):

    if filter_type == 'time':
        return await filter_time(update, context)
    
    query = update.callback_query
    await query.answer()

    try:
        current_message = query.message.text
        current_markup = query.message.reply_markup

        if filter_type == 'sport':
            options = {doc.to_dict().get("sport") for doc in db.collection("game").stream()}
            options.discard(None)
            title = "⚽ Select sports (multiple allowed):"
        elif filter_type == 'skill':
            options = {doc.to_dict().get("skill") for doc in db.collection("game").stream()}
            options.discard(None)
            title = "📊 Select skill levels (multiple allowed):"
        elif filter_type == 'date':
            options = {doc.to_dict().get("date") for doc in db.collection("game").stream()}
            options.discard(None)
            title = "📅 Select a date:"
        elif filter_type == 'venue':
            options = {doc.to_dict().get("venue") for doc in db.collection("game").stream()}
            options.discard(None)
            title = "📍 Pick venue/location (multiple allowed):"
        
        current_selection = context.user_data.get('filters', {}).get(filter_type, [])
        current_selection = [current_selection] if current_selection and not isinstance(current_selection,list) else current_selection or []

        keyboard = [
            [InlineKeyboardButton(
                f"{'✅ ' if opt in current_selection else ''}{opt}",
                callback_data=f"toggle_filter_{filter_type}_{opt.lower()}"
            )] for opt in options
        ]

        keyboard.append([
            InlineKeyboardButton("🧹 Clear Filters", callback_data=f"clear_{filter_type}_filters"),
            InlineKeyboardButton("🔙 Back", callback_data="back_to_filters"),
            InlineKeyboardButton("✅ Apply", callback_data=f"apply_filters_{filter_type}")
            ])
        
        new_markup = InlineKeyboardMarkup(keyboard)

        if current_message != title or str(current_markup) != str(new_markup):
            await query.edit_message_text(
                text=title,
                reply_markup=new_markup
            )
    
    
    except telegram.error.BadRequest as e:
        if "not modified" in str(e):
            pass
        else:
            raise

    return (SETTING_SPORTS if filter_type == 'sport' else
            SETTING_SKILL if filter_type == 'skill' else
            SETTING_DATE if filter_type == 'date' else
            SETTING_TIME if filter_type == 'time' else
            SETTING_VENUE)


async def filter_sport(update: Update,context: ContextTypes.DEFAULT_TYPE):
    return await show_filter_options(update, context, 'sport')

async def filter_skill(update: Update,context: ContextTypes.DEFAULT_TYPE):
    return await show_filter_options(update, context, 'skill')

async def filter_date(update: Update,context: ContextTypes.DEFAULT_TYPE):
    return await show_filter_options(update, context, 'date')

async def filter_time(update: Update,context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        time_slots = []
        for hour in range(7,24):
            for minute in [0,30]:   
                if hour == 23 and minute == 30:
                    continue
            start = f"{hour:02d}:{minute:02d}"
            end_hour = hour + (1 if minute == 30 else 0)
            end_minute = (minute + 30) % 60
            end = f"{end_hour % 24:02d}:{end_minute:02d}"
            time_slot = f"{start} - {end}"
            display_text = f"{hour}:{minute:02d}-{end_hour % 24}:{end_minute:02d}"
            time_slots.append((time_slot, display_text))

        current_selection = context.user_data.get('filters', {}).get('time', [])
        current_selection = [current_selection] if current_selection and not isinstance(current_selection,list) else current_selection or []
        
        keyboard = []
        for i in range(0, len(time_slots), 3):
            row = []
            for j in range(3):
                if i+j < len(time_slots):
                    slot, display = time_slots[i+j]
                    is_selected = '✅ ' if slot in current_selection else ''
                    row.append(InlineKeyboardButton(
                        text = f"{is_selected}{display}",
                        callback_data= f"toggle_filter_time_{slot}"
                    ))
            if row:
                keyboard.append(row)

        keyboard.append([
            InlineKeyboardButton("🧹 Clear Filters", callback_data=f"clear_time_filters"),
            InlineKeyboardButton("🔙 Back", callback_data="back_to_filters"),
            InlineKeyboardButton("✅ Apply", callback_data=f"apply_filters_time")
            ])
        
        await query.edit_message_text(
            "🕒 Select time ranges (multiple allowed):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except telegram.error.BadRequest as e:
        if "not modified" in str(e):
            pass
        else:
            raise
    except Exception as e:
        logging.error(f"Time filter error: {str(e)}")
        await query.edit_message_text("Couldnt update time selectiion. Please try again.")
    return SETTING_TIME

async def filter_venue(update: Update,context: ContextTypes.DEFAULT_TYPE):
    return await show_filter_options(update, context, 'venue')


async def toggle_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        parts = query.data.split('_')

        if len(parts) < 4:
            raise ValueError("Invalid callback data format")
        
        filter_type = parts[2]
        filter_value = '_'.join(parts[3:]).title()


        filters = context.user_data.setdefault('filters', {})
        selected = filters.get(filter_type, [])
    
        # Ensure it is a list
        selected = [selected] if selected and not isinstance(selected, list) else selected or []
        
        # Toggle selection
        if filter_value in selected:
            selected = [s for s in selected if s != filter_value]
        else:
            selected.append(filter_value)
        
        filters[filter_type] = selected

        filter_handlers = {
            'sport': filter_sport,
            'skill': filter_skill,
            'date': filter_date,
            'time': filter_time,
            'venue': filter_venue,
        }

        if filter_type in filter_handlers:
            try:
                return await filter_handlers[filter_type](update, context)
            except telegram.error.BadRequest as e:
                if "not modified" not in str(e):
                    raise
        else: 
            raise ValueError(f"Unknow filter type: {filter_type}")
    
    except Exception as e:
        logging.error(f"Toggle filter error: {str(e)}")
        await query.edit_message_text("An error occured. Please try again.")
        return await show_filter_menu(update, "🔍 Filter games by:", context)

async def apply_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        parts = query.data.split('_')
        if len(parts) < 3:
            raise ValueError("Invalid callback data format")
        
        filter_type = parts[2]

        context.user_data['page'] = 0

        if filter_type == 'sport':
            current_sports = context.user_data.get('filters', {}).get('sport', [])
            if not current_sports:
                await query.edit_message_text("ℹ️ Showing all sports - no filters applied")
        return await show_filter_menu(update, f"✅ {filter_type.title()} filters applied", context)
    
    except Exception as e:
        logging.error(f"Error apply filters: {str(e)}")
        await query.edit_message_text("Failed to apply filters. Please try again.")
        return await show_filter_menu (update, "🔍 Filter games by:", context)


async def save_text_filter(update: Update, context: ContextTypes.DEFAULT_TYPE, filter_key: str, filter_value: str) -> int:
    if filter_value.lower() != '/skip':
        context.user_data['filters'][filter_key] = filter_value
    return await show_filter_menu(update, f"✅ {filter_key.capitalize()} filter applied", context)

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    filters = context.user_data.get('filters', {})
    page = context.user_data.get('page', 0)
    games_ref = db.collection("game").where('status', '==', 'open')

    if time_ranges:= filters.get('time'):
        time_ranges = [time_ranges] if isinstance(time_ranges,str) else time_ranges


        def time_to_minutes(t):
            h, m = map(int, t.split(':'))
            return h*60+m

        games = []
        for doc in games_ref.stream():
            game_data = doc.to_dict()
            start = game_data.get('start_time_24')
            end = game_data.get('end_time_24')
            
            if not start or not end:
                continue

            g_start = time_to_minutes(start)
            g_end = time_to_minutes(end)

            for tr in time_ranges:
                if '-' in tr:
                    parts = tr.split('-')
                    if len(parts[1]) <= 2:
                        fixed_tr = f"{parts[0]}-{parts[1]}:00"
                    else:
                        fixed_tr = tr
                else:
                    continue

                time_parts = fixed_tr.split('-')
                if len(time_parts) != 2:
                    continue
                t_start = time_to_minutes(time_parts[0])
                t_end = time_to_minutes(time_parts[1])

                if None in (t_start, t_end):
                    continue

                if g_start <t_end and g_end >t_end:
                    game_data.update({
                        'id':doc.id,
                        'time_display': f"{start}-{end}"
                    })
                    games.append(game_data)
                    break
    else: 
        games = [{'id': doc.id, **doc.to_dict()} for doc in games_ref.stream()]

    if sports := filters.get('sport'):
        sports = [sports] if isinstance(sports, str) else sports
        games = [g for g in games if g.get('sport') in sports]

    if skills := filters.get('skill'):
        skills = [skills] if isinstance(skills, str) else skills
        games = [g for g in games if g.get('skill') in skills]

    if dates := filters.get('date'):
        dates = [dates] if isinstance(dates, str) else dates
        games = [g for g in games if g.get('date') in dates]

    if venues := filters.get('venue'):
        venues = [venues] if isinstance(venues, str) else venues
        games = [g for g in games if g.get('venue') in venues]

    context.user_data['games'] = games

    if not games:
        await query.edit_message_text("❌ No matching games found. Try different filters.")
        return await show_filter_menu (update, "🔍 Filter games by:", context)
    
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
        f"📅 <b>Date:</b> {game.get('date', 'N/A')}\n"
        f"🕒 <b>Time:</b> {game.get('start_time_24', 'N/A')} - {game.get('end_time_24', 'N/A')}\n"
        f"📍 <b>Venue:</b> {game.get('venue', 'N/A')}\n"
        f"📊 <b>Skill:</b> {game.get('skill', 'Any').title()}\n"
       # f"👥 <b>Players:</b> {len(game.get('players', []))} / {game.get('max_players',10)} "
       # f"{'(🏟️ FULL)' if len(game.get('players', [])) >= game.get('max_players', 10) else '✅ OPEN'}\n\n"
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
    

    #if len(game.get('players', [])) >= game.get('max_players', 10):
    #    await query.edit_message_text(" This game is already full")
    #    return BROWSE_GAMES

    game_ref = db.collection("game").document(game['id'])
    if update._effective_user.id in game.get('players_list', []):
        await query.edit_message_text("You've already joined this game")
        return BROWSE_GAMES


    await query.edit_message_text(
        f"✅ You've joined the {game.get('sport')} game! \n"
        f"Group: {game.get('group_link')}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Filters", callback_data="back_to_filters")]
        ])
    )
    return BROWSE_GAMES
