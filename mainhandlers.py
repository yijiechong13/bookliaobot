from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from savegame import GameDatabase
from host.utils import *
from host.hosthandlers import *

db = GameDatabase()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear() 

    keyboard = [
        [InlineKeyboardButton("🏟️ Host a Game", callback_data="host_game")],
        [InlineKeyboardButton("👥 Join a Game", callback_data="join_game")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome = (
        "🎉 Welcome to BookLiao Bot! \nNice to meet you! This bot helps NUS students organise or join casual sports games — anytime, anywhere. \n\n " \
        "You can: " \
        "\n 🏟️ Host a Game - set the sport, time, venue, and we'll help you find players " \
        "\n👥 Join a Game - browse open listings that match your schedule and interests \n\n " \
        "Let's get started! Choose an option below:"
    )

    if update.message:
        await update.message.reply_text(
            text=welcome,
            reply_markup=reply_markup
        )

    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=welcome,
            reply_markup=reply_markup
        )
    else:
        chat_id = update.effective_chat.id
        await context.bot.send_message(
            chat_id=chat_id,
            text=welcome,
            reply_markup=reply_markup
        )



async def save_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:

        game_data = context.user_data

        if not game_data['group_link'].startswith(("https://t.me/+", "https://telegram.me/")):
            await query.edit_message_text("❌ Invalid Telegram group link")
            return ConversationHandler.END
        
        game_doc_data = {
            "sport": game_data["sport"],
            "time": game_data["time"],  
            "venue": game_data["venue"], 
            "skill": game_data["skill"],
            "group_link": game_data["group_link"],
            "location": game_data.get("location", "other"),  
            "start_datetime": game_data.get("start_datetime"),  
            "end_datetime": game_data.get("end_datetime"), 
            "date_str": game_data.get("date_str", "unknown"), 
            "host": update.effective_user.id,
            "players": [update.effective_user.id],
            "status": "open",
        }
        
        game_id = db.save_game(game_doc_data)

        announcement_msg = await post_announcement(context, game_data, update.effective_user)
    
        db.update_game(game_id, {"announcement_msg_id": announcement_msg.message_id})
    
        await query.edit_message_text(
            text=f"✅ Game created and announced!\n\nView announcement: {announcement_msg.link}",
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
    
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear() 

    await update.message.reply_text("Cancelled. Use /start to begin again")
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.callback_query:
        await update.callback_query.message.reply_text(
            "⚠️ An error occurred. Please try again or /start"
        )
    elif update.message:
        await update.message.reply_text(
            "⚠️ An error occurred. Please try again or /start"
        )
    