import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils import validate_date_format, parse_time_input
from ..services.telethon_service import telethon_service
from bot.utils.constants import *
from fuzzywuzzy import process

load_dotenv() 

async def host_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer() 

    keyboard = [
        [InlineKeyboardButton("➕ Create New Game", callback_data="create_game")],
        [InlineKeyboardButton("📋 My Game Listings", callback_data="view_hosted_games")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]
    ]

    context.user_data.clear() 
    
    await query.edit_message_text(
        text="🏟️ Host a Game - Choose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return HOST_MENU

async def create_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer() 

    keyboard = [
        [InlineKeyboardButton("✅ Yes", callback_data="venue_yes")],
        [InlineKeyboardButton("❌ No", callback_data="venue_no")]
    ]

    context.user_data.clear() 

    # Set auto-create group flag
    context.user_data["auto_create_group"] = True
    
    await query.edit_message_text(
        text="Do you already have a venue booked?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ASK_BOOKING

async def handle_venue_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "venue_yes":
        
        if "booking_msg_id" in context.user_data and "booking_chat_id" in context.user_data:
            try:
                await context.bot.delete_message(
                    chat_id=context.user_data["booking_chat_id"],
                    message_id=context.user_data["booking_msg_id"]
                )
            except Exception as e:
                print(f"Couldn't delete message: {e}")
        
        # Clear the booking message data
        context.user_data.pop("booking_msg_id", None)
        context.user_data.pop("booking_chat_id", None)
        
        keyboard = [[InlineKeyboardButton(text, callback_data=data)] for text, data in SPORTS_LIST]
        
        await query.edit_message_text(
            "Which sport are you hosting?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SPORT

    elif query.data == "venue_no":
        print("✅ venue_no clicked")
        
        booking_keyboard = [
            [InlineKeyboardButton("🏫 NUS Facilities", url=BOOKING_URLS['NUS_FACILITIES'])],
            [InlineKeyboardButton("🏟️ ActiveSG Courts", url=BOOKING_URLS['ACTIVESG'])]
        ]
        booking_msg = await query.edit_message_text(
            "Please book your facility using one of the links below:",
            reply_markup=InlineKeyboardMarkup(booking_keyboard)
        ) 
        context.user_data["booking_msg_id"] = booking_msg.message_id
        context.user_data["booking_chat_id"] = booking_msg.chat_id

        done_keyboard = [[InlineKeyboardButton("✅ Done Booking", callback_data="done_booking")]]
        await query.message.reply_text(
            "Once you're done with the booking, tap the button below to continue:",
            reply_markup=InlineKeyboardMarkup(done_keyboard)
        ) 

        return WAITING_BOOKING_CONFIRM


async def after_booking (update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
      
    if "booking_msg_id" in context.user_data and "booking_chat_id" in context.user_data:
        try:
            await context.bot.delete_message(
                chat_id=context.user_data["booking_chat_id"],
                message_id=context.user_data["booking_msg_id"]
            )
            await query.message.delete()
        except Exception as e:
            print(f"Couldn't delete message: {e}")
    
    # Clear the booking message data
    context.user_data.pop("booking_msg_id", None)
    context.user_data.pop("booking_chat_id", None)
    
    if context.user_data.get("auto_create_group"):
        keyboard = []
        for text, data in SPORTS_LIST:
            keyboard.append([InlineKeyboardButton(str(text), callback_data=str(data))])

        await query.message.reply_text(
            "Which sport are you hosting?",
            reply_markup = InlineKeyboardMarkup(keyboard))
        return SPORT

async def sport_chosen (update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["sport"] = query.data
    await query.edit_message_text("Please enter the game date (dd/mm/yyyy):")
    return DATE

async def date_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    user_input = update.message.text
    
    is_valid, result = validate_date_format(user_input)

    if not is_valid: 
        await update.message.reply_text(f"❌ {result}\n\nPlease enter the date again:")
        return DATE
    
    context.user_data["date"] = result
    await update.message.reply_text("What time is the game? E.g 2pm-4pm")
    return TIME

async def time_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text

    time_data, error = parse_time_input(user_input)
    
    if error:
        await update.message.reply_text(error)
        return TIME
    
    context.user_data["time_display"] = time_data["display_format"]
    context.user_data["start_time_24"] = time_data["start_time_24"]
    context.user_data["end_time_24"] = time_data["end_time_24"]
    context.user_data["time_original"] = time_data["original_input"]
    
    await update.message.reply_text("Enter the venue/location:")
    return VENUE

async def venue_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()

    matches = []
    for venue, aliases in VENUES.items():
        all_names = aliases + [venue]
        best_match, score = process.extractOne(user_input, all_names)
        if score>40:
            matches.append((venue,score))

    if matches:
        matches.sort(key=lambda x: x[1], reverse=True)

        keyboard =[
            [InlineKeyboardButton(
                f"✅ {venue} (Similarity: {score}%)",
                callback_data=f"venue_confirm:{venue}"
            )] for venue, score in matches[:3]
        ]

        keyboard += [
            [InlineKeyboardButton(
                f"❌ Keep original: '{user_input}'",
                callback_data=f"venue_keep:{user_input}"
            )],
            [InlineKeyboardButton("🔄 Retype venue", callback_data="venue_retype")]
            ]
        await update.message.reply_text(
            "Did you mean one of these venues?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return VENUE_CONFIRM
    
    # If no matches from the list, proceed with original venue
    await update.message.reply_text(
        "Could not find any similar venues. Please check your spelling and try again."
    )
    return VENUE

async def venue_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("venue_confirm:"):
        venue = query.data.split(":", 1)[1].strip() 
        context.user_data["venue"] = venue
        
        # Continue to skill selection after confirming venue
        await query.edit_message_text(f"✅ Venue selected: {venue}")
        return await select_skill(update, context)
        
    elif query.data.startswith("venue_keep:"):
        venue = query.data.split(":", 1)[1]
        context.user_data["venue"] = venue
        
        await query.edit_message_text(f"✅ Venue selected: {venue}")
        return await select_skill(update, context)

    elif query.data == "venue_retype":

        context.user_data.pop('venue', None)
        await context.bot.send_message(
            chat_id =query.message.chat_id,
            text="Please enter the venue/location again:")
        return VENUE

    return VENUE_CONFIRM

async def select_skill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        message=update.message
    else:
        await update.callback_query.answer()
        message = update.callback_query.message

    keyboard = [
        [InlineKeyboardButton(skill, callback_data=skill)] for skill in SKILL_LEVELS
    ]

    await context.bot.send_message(
        chat_id=message.chat_id,
        text="Select skill level:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SKILL

async def skill_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["skill"] = query.data

    game_data = context.user_data

    summary = (
        f"🏟️ New Game Listing:\n\n"
        f"🎖️ Sport: {game_data['sport']}\n"
        f"📅 Date: {game_data['date']}\n"
        f"🕒 Time: {game_data['time_display']}\n"
        f"📍 Venue: {game_data['venue']}\n"
        f"📊 Skill: {game_data['skill'].title()}\n"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data="confirm_game")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_game")],
    ]
    
    await query.edit_message_text(
        text=summary,reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRMATION

async def save_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    db = context.bot_data['db']
    reminder_service = context.bot_data['reminder_service']

    try:

        game_data = context.user_data

        if context.user_data.get("auto_create_group"):
            loading_msg = await query.edit_message_text(
                text="🔄 Creating your game group... Please wait!",
                reply_markup=None
            ) 
            
            group_result = await telethon_service.create_game_group(
                game_data, 
                update.effective_user
            )
            
            if group_result:
                game_data["group_link"] = group_result["group_link"]
                game_data["group_id"] = group_result["group_id"]
                game_data["group_name"] = group_result["group_name"]
                
                await loading_msg.edit_text(
                    text="✅ Group created successfully! Saving game...",
                    reply_markup=None
                )
            else:
                await loading_msg.edit_text(
                    text="❌ Failed to create group. Please try again. ",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Try Again", callback_data="confirm_game")],
                        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_game")]
                    ])
                )
                return CONFIRMATION
            
        initial_player_count = 1 #Host is the first player    
        
        game_doc_data = {
            "sport": game_data["sport"],
            "date": game_data["date"],
            "time_display": game_data["time_display"],  
            "venue": game_data["venue"], 
            "skill": game_data["skill"],
            "group_link": game_data["group_link"], 
            "start_time_24": game_data["start_time_24"],
            "end_time_24": game_data["end_time_24"],      
            "host": update.effective_user.id,
            "status": "open",
            "group_id": str(group_result["group_id"]), 
            "reminder_24h_sent": False,
            "reminder_2h_sent": False,
            "player_count": initial_player_count,
            "host_username": update.effective_user.username
        }
        
        game_id = db.save_game(game_doc_data)

        try:
            await reminder_service.schedule_game_reminders(context, game_doc_data, game_id)
            print(f"✅ Reminders scheduled for new game {game_id}")
        except Exception as reminder_error:
            print(f"⚠️ Error scheduling reminders for game {game_id}: {reminder_error}")
    

        announcement_data = {
            "sport": game_data["sport"],
            "date": game_data["date"],
            "time_display": game_data["time_display"],  
            "venue": game_data["venue"],
            "skill": game_data["skill"],
            "group_link": game_data["group_link"],
            "player_count": initial_player_count,
            "host_username": update.effective_user.username
        }

        announcement_msg = await post_announcement(context, announcement_data, update.effective_user)

        #Store announcement message id for status updates later on 
        db.update_game(game_id, {"announcement_msg_id": announcement_msg.message_id})
    
       
        if context.user_data.get("auto_create_group"):
            success_text = f"\n🎉 Group '{game_data.get('group_name')}' created and announced!"
        
        success_text += f"\n\nView announcement: {announcement_msg.link}"

        await query.edit_message_text(
            text=success_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Join Group", url=game_data["group_link"])]
            ])
        )

        context.user_data.clear()
        return ConversationHandler.END
   
    except Exception as e:
        print(f"Error saving game: {str(e)}")

        await query.edit_message_text(
            text ="⚠️ Failed to save game. Please try again.",
            reply_markup=None
            )
        return ConversationHandler.END

async def post_announcement(context, game_data, user):
    ANNOUNCEMENT_CHANNEL = os.getenv("ANNOUNCEMENT_CHANNEL")
    announcement_text = (
        f"🏟️ New {game_data['sport']} Game!\n\n"
        f"📅 Date: {game_data['date']}\n"
        f"🕒 Time: {game_data['time_display']}\n"
        f"📍 Venue: {game_data['venue']}\n"
        f"📊 Skill Level: {game_data['skill'].title()}\n"
        f"👥 Players: {game_data.get('player_count', 1)}\n"
        f"👤 Host: @{user.username or 'Anonymous'}\n\n"
        f"🔗 Join Group: {game_data['group_link']}"
    )

    return await context.bot.send_message(
        chat_id=ANNOUNCEMENT_CHANNEL,
        text=announcement_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✋ Join Game", url=game_data["group_link"])]
        ])
    )