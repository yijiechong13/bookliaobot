from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils import *
from createagame import *


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear() 

    keyboard = [
        [InlineKeyboardButton("🏟️ Host a Game", callback_data="host_game")],
        [InlineKeyboardButton("👥 Join a Game", callback_data="join_game")],
    ]
    await update.message.reply_text(
        "🎉 Welcome to BookLiao Bot! \nNice to meet you! This bot helps NUS students organise or join casual sports games — anytime, anywhere. \n\n " \
        "You can: " 
        "\n 🏟️ Host a Game - set the sport, time, venue, and we'll help you find players " \
        "\n👥 Join a Game - browse open listings that match your schedule and interests \n\n " \
        "Let's get started! Choose an option below:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
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
    