import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils import *

load_dotenv() 

#Conversation states for hosting game
ASK_BOOKING, WAITING_BOOKING_CONFIRM, WAITING_FOR_GROUP_LINK,GET_GROUP_LINK, RECEIVED_GROUP_LINK, SPORT, TIME, VENUE, SKILL, CONFIRMATION = range(10)

async def host_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer() 

    keyboard = [
        [InlineKeyboardButton("✅ Yes", callback_data="venue_yes")],
        [InlineKeyboardButton("❌ No", callback_data="venue_no")]
    ]

    context.user_data.clear() 
    
    await query.edit_message_text(
        text="Do you already have a venue booked?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ASK_BOOKING


async def handle_venue_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "venue_yes":
        await after_booking(update,context)
        return WAITING_FOR_GROUP_LINK

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
    
    keyboard = [
        [InlineKeyboardButton("✅ Yes", callback_data="group_yes")],
        [InlineKeyboardButton("❌ No", callback_data="group_no")]
    ]
    await query.edit_message_text("Have you created a Telegram group for this game?", reply_markup=InlineKeyboardMarkup(keyboard))
    
    return WAITING_FOR_GROUP_LINK

async def handle_telegram_group_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()


    if query.data == "group_yes":
        await get_group_link(update, context)  
        return RECEIVED_GROUP_LINK
    
    elif query.data == "group_no":
        await query.edit_message_text(
            "Please create a Telegram group and add @BookLiaoBot as an admin.\n"
            "Once done, come back and tap the button below.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Done Creating Group", callback_data="group_yes")]
            ])
        )
        return GET_GROUP_LINK

async def get_group_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("Please paste your telegram group link: e.g https://t.me/+H-Ta2vuZmDE1Mjg2 ", reply_markup=None)
    return RECEIVED_GROUP_LINK  

async def receive_group_link(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    context.user_data["group_link"] = update.message.text   

    if not update.message.text.startswith(("https://t.me/+", "https://telegram.me/")):
        await update.message.reply_text("❌ That doesn't look like a valid Telegram group link. Try again:")
        return RECEIVED_GROUP_LINK

    sports = ["⚽ Football", "🏀 Basketball", "🎾 Tennis", "🏐 Volleyball"]
    keyboard = [[InlineKeyboardButton(sport, callback_data=sport[2:])] for sport in sports]

    await update.message.reply_text(
        "which sport are you hosting?",
        reply_markup = InlineKeyboardMarkup(keyboard))
    return SPORT

async def sport_chosen (update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["sport"] = query.data
    await query.edit_message_text("What time is the game? (e.g., 'Today 6pm-8pm' or 'Saturday 2pm-4pm'):"
    )
    return TIME


async def time_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    context.user_data["time"] = user_input

    parsed_time = parse_time_input(user_input)

    if parsed_time:
        context.user_data["start_datetime"] = parsed_time["start"]
        context.user_data["end_datetime"] = parsed_time["end"]
        context.user_data["date_str"] = parsed_time["date_str"]  
        
        await update.message.reply_text("Enter venue/location:")
        return VENUE
    
    else:
        await update.message.reply_text(
            "⚠️ I couldn't understand the time format. Please try again with formats like:\n"
            "• 'Today 6pm-8pm'\n"
            "• 'Tomorrow 2pm-4pm'\n"
            "• 'Saturday 10am-12pm'\n"
            "• 'Dec 25 3pm-5pm'"
        )
        return TIME
    
async def venue_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    context.user_data["venue"] = update.message.text

   
    parsed_location = parse_location(user_input)
    context.user_data["location"] = parsed_location

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
        f"🕒 Time: {game_data['time']}\n"
        f"📍 Venue: {game_data['venue']}\n"
        f"📊 Skill: {game_data['skill'].title()}\n"
        f"🔗Telegram link: {game_data['group_link']}\n"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data="confirm_game")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_game")],
    ]
    
    await query.edit_message_text(
        text=summary,reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRMATION

async def post_announcement(context, game_data, user):
    
    ANNOUNCEMENT_CHANNEL = os.getenv("ANNOUNCEMENT_CHANNEL")
    announcement_text = (
        f"🎮 New {game_data['sport']} Game!\n\n"
        f"🕒 Time: {game_data['time']}\n"
        f"📍 Venue: {game_data['venue']}\n"
        f"📊 Skill Level: {game_data['skill'].title()}\n"
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