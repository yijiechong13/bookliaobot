import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils import *
from config import *


load_dotenv() 

async def view_hosted_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    db = context.bot_data['db']
    
    user_id = update.effective_user.id
    games = db.get_hosted_games(user_id)
    
    if not games:
        await query.edit_message_text(
            text= "You don't have any active game listings.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Create New Game", callback_data="create_game")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
            ])
        )
        return HOST_MENU
    
    context.user_data["hosted_games"] = games
    context.user_data["current_game_index"] = 0
    
    await display_game(update, context)
    return VIEW_HOSTED_GAMES

async def display_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    games = context.user_data["hosted_games"]
    current_index = context.user_data["current_game_index"]
    game = games[current_index]
    
    text = (
        f"📋 Your Game Listing ({current_index + 1}/{len(games)}):\n\n"
        f"🏀 Sport: {game['sport']}\n"
        f"🕒 Time: {game['time_display']}\n"
        f"📍 Venue: {game['venue']}\n"
        f"📊 Skill: {game['skill'].title()}\n"
        f"🔗 Group: {game['group_link']}\n"
        f"🟢 Status: {game['status'].title()}"
    )
    
    keyboard = []
    
    if len(games) > 1:
        nav_buttons = []
        if current_index > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data="prev_game"))
        if current_index < len(games) - 1:
            nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data="next_game"))
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("❌ Cancel Game", callback_data="cancel_game_prompt")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")])
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return VIEW_HOSTED_GAMES

async def navigate_hosted_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try: 
        if query.data == "prev_game":
            context.user_data["current_game_index"] -= 1
        elif query.data == "next_game":
            context.user_data["current_game_index"] += 1
    
        await display_game(update, context)
        return VIEW_HOSTED_GAMES

    except Exception as e:
        print(f"Navigation error: {e}")
        await query.edit_message_text("⚠️ Navigation failed. Use /start to begin again.")
        return ConversationHandler.END

async def cancel_game_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="⚠️ Are you sure you want to cancel this game?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Cancel", callback_data="confirm_cancel")],
            [InlineKeyboardButton("❌ No, Keep It", callback_data="back_to_list")]
        ])
    )
    return CONFIRM_CANCEL

async def confirm_cancel_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    db = context.bot_data['db']
    
    games = context.user_data["hosted_games"]
    current_index = context.user_data["current_game_index"]
    game = games[current_index]
    
    # Update database
    announcement_msg_id = db.cancel_game(game['id'])
    
    #Update announcement channel message 
    if announcement_msg_id:
        ANNOUNCEMENT_CHANNEL = os.getenv("ANNOUNCEMENT_CHANNEL")
        try:
            await context.bot.edit_message_text(
                chat_id=ANNOUNCEMENT_CHANNEL,
                message_id=announcement_msg_id,
                text=f"❌ CANCELLED: {game['sport']} Game at {game['venue']} on {game['time']}"
            )
        except Exception as e:
            print(f"Couldn't update announcement: {e}")
    
    # Remove the cancelled game from the list
    games.pop(current_index)
    
    if not games:
        await query.edit_message_text(
            text="✅ Game cancelled. You have no more active listings.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Create New Game", callback_data="create_game")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
            ])
        )
        return HOST_MENU
    
    # Adjust current index if needed
    if context.user_data["current_game_index"] >= len(games):
        context.user_data["current_game_index"] = len(games) - 1
    
    await display_game(update, context)
    return VIEW_HOSTED_GAMES

async def back_to_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await display_game(update, context)
    return VIEW_HOSTED_GAMES

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data.clear()

    keyboard = [
        [InlineKeyboardButton("🏟️ Host a Game", callback_data="host_game")],
        [InlineKeyboardButton("👥 Join a Game", callback_data="join_game")],
    ]

    try:
        await query.edit_message_text(
            text="🎉 Welcome to BookLiao Bot! \nNice to meet you! This bot helps NUS students organise or join casual sports games — anytime, anywhere. \n\n " \
        "You can: " 
        "\n 🏟️ Host a Game - set the sport, time, venue, and we'll help you find players " \
        "\n👥 Join a Game - browse open listings that match your schedule and interests \n\n " \
        "Let's get started! Choose an option below:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        print(f"Error returning to main: {e}")
        await update.effective_message.reply_text(
            text="🏠 Main Menu\nWhat would you like to do?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return ConversationHandler.END
    