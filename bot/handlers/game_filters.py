from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from ..utils import *
from ..utils.constants import *
import logging
import telegram


async def show_filter_menu(update: Update, text: str, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        filters = context.user_data.get('filters', {})
        val = lambda v: v and (not isinstance(v, (list, dict, str)) or bool(v))

        buttons = [
            [f"🎖️ Sports {'✅' if val(filters.get('sport')) else ''}", "filter_sport"],
            [f"📅 Date {'✅' if val(filters.get('date')) else ''}", "filter_date"],
            [f"🕒 Time {'✅' if val(filters.get('time')) else ''}", "filter_time"],
            [f"📍 Venue {'✅' if val(filters.get('venue')) else ''}", "filter_venue"],
            [f"📊 Skill {'✅' if val(filters.get('skill')) else ''}", "filter_skill"],
            ["🔍 Show Results", "show_results"],
        ]

        keyboard = [
            [InlineKeyboardButton(text, callback_data=data)]
            for text, data in buttons
        ]

        keyboard.append([
            InlineKeyboardButton("🧹 Clear All", callback_data="clear_filters"),
            InlineKeyboardButton("💾 Save", callback_data="save_preferences"), 
            InlineKeyboardButton("🔙 Back", callback_data="start"),
        ])
        
        # Filters summary
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
        logging.error(f"Error in show_filter_menu: {str(e)}")
        if update.callback_query:
            await update.callback_query.message.reply_text("⚠️ Menu error. Please try again.")
        return ConversationHandler.END

async def show_filter_options(update: Update, context: ContextTypes.DEFAULT_TYPE, filter_type: str):
    if filter_type == 'time':
        return await filter_time(update, context)
    
    query = update.callback_query
    await query.answer()

    try:
        current_message = query.message.text
        current_markup = query.message.reply_markup

        # Use predefined lists for sport and skill, Firebase data for others
        if filter_type == 'sport':
            options = [display for display, value in SPORTS_LIST]
            title = "🎖️Select sports (multiple allowed):"
        elif filter_type == 'skill':
            options = SKILL_LEVELS 
            title = "📊 Select skill levels (multiple allowed):"
        else:
            # For date and venue, get from Firebase
            games_ref = context.bot_data['db'].db.collection("game").where('status', '==','open')
            
            if filter_type == 'date':
                options = {doc.to_dict().get("date") for doc in games_ref.stream()}
                options.discard(None)
                options = list(options)
                title = "📅 Select a date:"
            elif filter_type == 'venue':
                options = {doc.to_dict().get("venue") for doc in games_ref.stream()}
                options.discard(None)
                options = list(options)
                title = "📍 Pick venue/location (multiple allowed):"
        
        current_selection = context.user_data.get('filters', {}).get(filter_type, [])
        current_selection = [current_selection] if current_selection and not isinstance(current_selection,list) else current_selection or []

        keyboard = []
        for opt in options:
            if filter_type == 'sport':
                actual_value = next((value for display, value in SPORTS_LIST if display == opt), opt)
                is_selected = actual_value in current_selection
            elif filter_type == 'skill':
                actual_value = opt if opt in SKILL_LEVELS else opt
                is_selected = actual_value in current_selection
            else:
                is_selected = opt in current_selection
            
            keyboard.append([InlineKeyboardButton(
                f"{'✅ ' if is_selected else ''}{opt}",
                callback_data=f"toggle_filter_{filter_type}_{opt.lower()}"
            )])
        
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

async def filter_sport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await show_filter_options(update, context, 'sport')

async def filter_skill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await show_filter_options(update, context, 'skill')

async def filter_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await show_filter_options(update, context, 'date')

async def filter_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await query.edit_message_text("❌ Couldn't update time selection. Please try again.")
    return SETTING_TIME

async def filter_venue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await show_filter_options(update, context, 'venue')

async def toggle_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        parts = query.data.split('_')

        if len(parts) < 4:
            raise ValueError("Invalid callback data format")
        
        filter_type = parts[2]
        filter_value = '_'.join(parts[3:])
        
        if filter_type == 'sport':
            sport_map = {display.lower(): value for display, value in SPORTS_LIST}
            filter_value = sport_map.get(filter_value.lower(), filter_value.title())
        elif filter_type == 'skill':
            skill_map = {skill.lower(): skill for skill in SKILL_LEVELS}
            filter_value = skill_map.get(filter_value.lower(), filter_value.title())
        else:
            filter_value = filter_value.title()

        filters = context.user_data.setdefault('filters', {})
        selected = filters.get(filter_type, [])
    
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
            raise ValueError(f"Unknown filter type: {filter_type}")
    
    except Exception as e:
        logging.error(f"Toggle filter error: {str(e)}")
        await query.edit_message_text("An error occurred. Please try again.")
        return await show_filter_menu(update, "🔍 Filter games by:", context)

async def apply_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        filter_type = query.data.split('_')[2]
        context.user_data['page'] = 0

        if not context.user_data.get('filters', {}).get(filter_type):
            msgs = {
                'sport': "🎖️ All sports",
                'skill': "📊 All skills",
                'date': "📅 All dates",
                'time': "🕒 All times",
                'venue': "📍 All venues"
            }
            await query.edit_message_text(f"ℹ️ Showing {msgs.get(filter_type, 'all')} - no filters applied")
        
        return await show_filter_menu(update, f"✅ {filter_type.title()} filters applied", context)
    
    except Exception as e:
        logging.error(f"Error applying filters: {str(e)}")
        await query.edit_message_text("❌ Failed to apply filters. Please try again.")
        return await show_filter_menu(update, "🔍 Filter games by:", context)

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    db = context.bot_data['db']
    filters = context.user_data.get('filters', {})

    # Auto-save preferences when showing results
    from .user_preferences import save_user_preferences
    user_id = str(update.effective_user.id)
    await save_user_preferences(user_id, filters, db)

    page = context.user_data.get('page', 0)
    games_ref = db.db.collection("game").where('status', '==', 'open')

    if time_ranges := filters.get('time'):
        time_ranges = [time_ranges] if isinstance(time_ranges, str) else time_ranges

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

                if g_start < t_end and g_end > t_start:
                    game_data.update({
                        'id': doc.id,
                        'time_display': f"{start}-{end}"
                    })
                    games.append(game_data)
                    break
    else: 
        games = [{'id': doc.id, **doc.to_dict()} for doc in games_ref.stream()]

    # Apply other filters
    if sport := filters.get('sport'):
        sport = [sport] if isinstance(sport, str) else sport
        games = [g for g in games if g.get('sport') in sport]

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
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_filters")]
        ])
        
        await query.edit_message_text(
            text="❌ No matching games found. Try different filters.",
            reply_markup=reply_markup
        )
        return BROWSE_GAMES
    
    page %= len(games)
    context.user_data['page'] = page
    game = games[page]

    try:
        game_ref = db.db.collection("game").document(game['id'])
        game_doc = game_ref.get()
        
        if game_doc.exists:
            fresh_game_data = game_doc.to_dict()
            game.update(fresh_game_data)
            game['id'] = game_doc.id
            
            players_list = fresh_game_data.get('players_list', [])
            member_count = len(players_list)
            firebase_player_count = fresh_game_data.get('player_count', 0)
            member_count = max(member_count, firebase_player_count)
        else:
            logging.warning(f"Game document {game['id']} not found in Firebase")
            member_count = game.get('player_count', 1)
            
    except Exception as e:
        logging.error(f"Error fetching fresh game data: {str(e)}")
        players_list = game.get('players_list', [])
        member_count = len(players_list) if players_list else game.get('player_count', 1)

    context.user_data['current_game'] = game

    filters_summary = "\n".join(
        [f"• {k.capitalize()}: {v}" for k, v in filters.items()]
    ) or "None"

    game_info = (
        f"🎯 <b>Matching Game #{page+1}</b>\n\n"
        f"🎖️ <b>Sport:</b> {game.get('sport', 'N/A').title()}\n"
        f"📅 <b>Date:</b> {game.get('date', 'N/A')}\n"
        f"🕒 <b>Time:</b> {game.get('start_time_24', 'N/A')} - {game.get('end_time_24', 'N/A')}\n"
        f"📍 <b>Venue:</b> {game.get('venue', 'N/A')}\n"
        f"📊 <b>Skill:</b> {game.get('skill', 'Any').title()}\n"
        f"👥 <b>Players:</b> {member_count}\n"
        f"🔗 <b>Group:</b> {game.get('group_link', 'Not available')}\n\n"
        f"🔎 <b>Filters applied:</b> {filters_summary}"
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
        InlineKeyboardButton("🔙 Back", callback_data="back_to_filters"),
    ]

    reply_markup = InlineKeyboardMarkup([buttons, action] if buttons else [action])

    await query.edit_message_text(
        game_info,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

    return BROWSE_GAMES

async def handle_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
    db = context.bot_data['db']

    if not game.get('id'):
        await query.edit_message_text("Invalid game selected")
        return BROWSE_GAMES

    if update._effective_user.id in game.get('players_list', []):
        await query.edit_message_text("You've already joined this game")
        return BROWSE_GAMES

    await query.edit_message_text(
        f"✅ Click the link below to join the {game.get('sport')} game! \n"
        f"Group: {game.get('group_link')}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_filters")]
        ])
    )
    return BROWSE_GAMES