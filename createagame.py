import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils import validate_date_format, parse_time_input
from telethon_service import telethon_service
from config import *

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
        
        # Show sport selection
        sports = ["⚽ Football", "🏀 Basketball", "🎾 Tennis", "🏐 Volleyball"]
        keyboard = [[InlineKeyboardButton(sport, callback_data=sport[2:])] for sport in sports]

        await query.edit_message_text(
            "Which sport are you hosting?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SPORT

    elif query.data == "venue_no":
        print("✅ venue_no clicked")
        
        booking_keyboard = [
            [InlineKeyboardButton("🏫 NUS Facilities", url="https://reboks.nus.edu.sg/nus_public_web/public/facilities")],
            [InlineKeyboardButton("🏟️ ActiveSG Courts", url="https://activesg.gov.sg/activities/list")]
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
        except Exception as e:
            print(f"Couldn't delete message: {e}")
    
    
    context.user_data.pop("booking_msg_id", None)
    context.user_data.pop("booking_chat_id", None)
    
    if context.user_data.get("auto_create_group"):
        sports = ["⚽ Football", "🏀 Basketball", "🎾 Tennis", "🏐 Volleyball"]
        keyboard = [[InlineKeyboardButton(sport, callback_data=sport[2:])] for sport in sports]

        await update.message.reply_text(
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
    
    is_valid, date = validate_date_format(user_input)

    if not is_valid: 
        await update.message.reply_text(f"❌{date}\n\nPlease enter the date again:")
        return DATE
    
    context.user_data["date"] = date
    await update.message.reply_text("What time is the game? E.g 2pm-4pm")
    return TIME

async def time_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text

    time_data, error = parse_time_input(user_input)
    
    if error:
        await update.message.reply_text(
            f"❌ {error}\n\n"
            "Please try again with formats like:\n"
            "• 2pm-4pm\n"
            "• 14:00-16:00\n"
            "• 2:30pm-4:30pm"
        )
        return TIME
    
    context.user_data["time_display"] = time_data["display_format"]
    context.user_data["start_time_24"] = time_data["start_time_24"]
    context.user_data["end_time_24"] = time_data["end_time_24"]
    context.user_data["time_original"] = time_data["original_input"]
    
    await update.message.reply_text("Enter the venue/location:")
    return VENUE
    
    
async def venue_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["venue"] = update.message.text

    keyboard = [
        [InlineKeyboardButton("Beginner", callback_data="Beginner")],
        [InlineKeyboardButton("Intermediate", callback_data="Intermediate")],
        [InlineKeyboardButton("Advanced", callback_data="Advanced")]
    ]

    await update.message.reply_text(
        "Select skill level:",
        reply_markup=InlineKeyboardMarkup(keyboard))
    return SKILL

async def skill_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["skill"] = query.data

    game_data = context.user_data

    summary = (
        f"🏟️ New Game Listing:\n\n"
        f"🏀 Sport: {game_data['sport']}\n"
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
            "group_id": game_data.get("group_id"), 
            "reminder_24h_sent": False,
            "player_count": initial_player_count
        }
        
        game_id = db.save_game(game_doc_data)

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
        f"🎮 New {game_data['sport']} Game!\n\n"
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


