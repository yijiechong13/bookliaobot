import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from ..utils import ValidationHelper, DateTimeHelper
from ..utils.constants import *

load_dotenv() 

class HostedGamesService:
    
    @staticmethod
    def create_main_menu_keyboard():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🏟️ Host a Game", callback_data="host_game")],
            [InlineKeyboardButton("👥 Join a Game", callback_data="join_game")],
        ])
    
    @staticmethod
    def create_empty_games_keyboard():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Create New Game", callback_data="create_game")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
        ])
    
    @staticmethod
    def create_game_navigation_keyboard(games, current_index):
        keyboard = []
        
        # Navigation buttons if there are multiple games
        if len(games) > 1:
            nav_buttons = []
            if current_index > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data="prev_game"))
            if current_index < len(games) - 1:
                nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data="next_game"))
            if nav_buttons:
                keyboard.append(nav_buttons)
   
        keyboard.extend([
            [InlineKeyboardButton("❌ Cancel Game", callback_data="cancel_game_prompt")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_confirmation_keyboard():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Cancel", callback_data="confirm_cancel")],
            [InlineKeyboardButton("❌ No, Keep It", callback_data="back_to_list")]
        ])
    
    @staticmethod
    def format_game_display(game, current_index, total_games):
        return (
            f"📋 Your Game Listing ({current_index + 1}/{total_games}):\n\n"
            f"🎖️ Sport: {game['sport']}\n"
            f"📅 Date: {game['date']}\n"
            f"🕒 Time: {game['time_display']}\n"
            f"📍 Venue: {game['venue']}\n"
            f"📊 Skill: {game['skill'].title()}\n"
            f"🔗 Group: {game['group_link']}\n"
        )
    
    @staticmethod
    def get_welcome_message():
        return (
            "🎉 Welcome to BookLiao Bot! \n"
            "Nice to meet you! This bot helps NUS students organise or join casual sports games — anytime, anywhere. \n\n"
            "You can: "
            "\n 🏟️ Host a Game - set the sport, time, venue, and we'll help you find players "
            "\n👥 Join a Game - browse open listings that match your schedule and interests \n\n"
            "Let's get started! Choose an option below:"
        )
    
    @staticmethod
    async def safe_query_answer(query):
        try:
            if query and not query.answered:
                await query.answer()
        except Exception as e:
            print(f"Warning: Could not answer query: {e}")
    
    @staticmethod
    async def safe_edit_message(query, text, reply_markup=None, fallback_message=None):
        try:
            if query and query.message:
                await query.edit_message_text(text=text, reply_markup=reply_markup)
                return True
        except Exception as e:
            print(f"Error editing message: {e}")
            if fallback_message and query and query.message:
                try:
                    await query.message.reply_text(text=fallback_message, reply_markup=reply_markup)
                    return True
                except Exception as fallback_error:
                    print(f"Fallback message also failed: {fallback_error}")
            return False

async def view_hosted_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await HostedGamesService.safe_query_answer(query)
    
    try:
        # Check if db exists
        db = context.bot_data.get('db')
        if not db:
            print("❌ Database not found in context")
            await query.edit_message_text("❌ System error. Please try again later.")
            return ConversationHandler.END
        
        user_id = update.effective_user.id
        print(f"🔍 Fetching hosted games for user {user_id}")
        
        games = await db.get_hosted_games(context, user_id)
        print(f"✅ Found {len(games) if games else 0} games for user {user_id}")
        
        if not games:
            await HostedGamesService.safe_edit_message(
                query,
                "You don't have any active game listings.",
                HostedGamesService.create_empty_games_keyboard()
            )
            return HOST_MENU
        
        # Store games data and initialize navigation
        context.user_data["hosted_games"] = games
        context.user_data["current_game_index"] = 0
        print(f"✅ Stored {len(games)} games in context, index set to 0")
        
        await display_game(update, context)
        return VIEW_HOSTED_GAMES
        
    except Exception as e:
        print(f"❌ Error in view_hosted_games: {e}")
        import traceback
        traceback.print_exc()
        await query.edit_message_text("❌ Failed to load your games. Please try again.")
        return ConversationHandler.END

async def display_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await HostedGamesService.safe_query_answer(query)
    
    try:
        # Check if we have the required data
        games = context.user_data.get("hosted_games")
        current_index = context.user_data.get("current_game_index")
        
        if not games:
            print("❌ No games data found in context")
            await query.edit_message_text("❌ No games found. Please start over.")
            return ConversationHandler.END
        
        if current_index is None:
            print("❌ No current_game_index found, setting to 0")
            current_index = 0
            context.user_data["current_game_index"] = 0
        
        if not (0 <= current_index < len(games)):
            print(f"❌ Invalid game index: {current_index} for {len(games)} games, resetting to 0")
            context.user_data["current_game_index"] = 0
            current_index = 0
        
        game = games[current_index]
        print(f"✅ Displaying game {current_index + 1}/{len(games)}: {game.get('sport', 'Unknown')}")
        

        text = HostedGamesService.format_game_display(game, current_index, len(games))
        keyboard = HostedGamesService.create_game_navigation_keyboard(games, current_index)
        
        await HostedGamesService.safe_edit_message(query, text, keyboard)
        return VIEW_HOSTED_GAMES
        
    except Exception as e:
        print(f"❌ Error in display_game: {e}")
        print(f"Context data: games={len(context.user_data.get('hosted_games', []))}, index={context.user_data.get('current_game_index')}")
        await query.edit_message_text("❌ Display error. Please try again with /start")
        return ConversationHandler.END

async def navigate_hosted_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await HostedGamesService.safe_query_answer(query)
    
    try:
        current_index = context.user_data.get("current_game_index", 0)
        games = context.user_data.get("hosted_games", [])
        
        if not games:
            await query.edit_message_text("❌ No games to navigate.")
            return ConversationHandler.END
        
        # Update index based on navigation direction
        if query.data == "prev_game" and current_index > 0:
            context.user_data["current_game_index"] = current_index - 1
        elif query.data == "next_game" and current_index < len(games) - 1:
            context.user_data["current_game_index"] = current_index + 1
        else:
            print(f"Invalid navigation: {query.data} at index {current_index}")
    
        await display_game(update, context)
        return VIEW_HOSTED_GAMES

    except Exception as e:
        print(f"Navigation error: {e}")
        await query.edit_message_text("⚠️ Navigation failed. Use /start to begin again.")
        return ConversationHandler.END

async def cancel_game_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await HostedGamesService.safe_query_answer(query)
    
    keyboard = HostedGamesService.create_confirmation_keyboard()
    await HostedGamesService.safe_edit_message(
        query,
        "⚠️ Are you sure you want to cancel this game?",
        keyboard
    )
    return CONFIRM_CANCEL

async def confirm_cancel_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await HostedGamesService.safe_query_answer(query)

    required_fields = ["hosted_games", "current_game_index"]
    if not ValidationHelper.validate_required_fields(context.user_data, required_fields)[0]:
        await query.edit_message_text("❌ Error: Missing game data. Please start over.")
        return ConversationHandler.END

    db = context.bot_data['db']
    games = context.user_data["hosted_games"]
    current_index = context.user_data["current_game_index"]
    
    if not (0 <= current_index < len(games)):
        await query.edit_message_text("❌ Invalid game selection.")
        return ConversationHandler.END
    
    game = games[current_index]
    
    try:
        # Cancel game in database
        announcement_msg_id = db.cancel_game(game['id'])
        
        # Update announcement channel message 
        await _update_announcement_message(context, announcement_msg_id, game)
        
        # Remove cancelled game from local list
        games.pop(current_index)
        
        # Handle empty games list
        if not games:
            await HostedGamesService.safe_edit_message(
                query,
                "✅ Game cancelled. You have no more active listings.",
                HostedGamesService.create_empty_games_keyboard()
            )
            return HOST_MENU
        
        # Adjust index if necessary
        if current_index >= len(games):
            context.user_data["current_game_index"] = len(games) - 1
        
        await display_game(update, context)
        return VIEW_HOSTED_GAMES
        
    except Exception as e:
        print(f"Error cancelling game: {e}")
        await query.edit_message_text("❌ Failed to cancel game. Please try again.")
        return VIEW_HOSTED_GAMES

async def _update_announcement_message(context, announcement_msg_id, game):
    if not announcement_msg_id:
        return
        
    announcement_channel = os.getenv("ANNOUNCEMENT_CHANNEL")
    if not announcement_channel:
        print("Warning: ANNOUNCEMENT_CHANNEL not configured")
        return
    
    try:
        cancelled_text = f"❌ CANCELLED: {game['sport']} Game at {game['venue']} on {game['time_display']}"
        await context.bot.edit_message_text(
            chat_id=announcement_channel,
            message_id=announcement_msg_id,
            text=cancelled_text,
            reply_markup=None
        )
        print(f"✅ Updated announcement message {announcement_msg_id}")
    except Exception as e:
        print(f"Warning: Couldn't update announcement message: {e}")

async def back_to_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await HostedGamesService.safe_query_answer(query)
    
    await display_game(update, context)
    return VIEW_HOSTED_GAMES

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await HostedGamesService.safe_query_answer(query)

    context.user_data.clear()

    keyboard = HostedGamesService.create_main_menu_keyboard()
    welcome_message = HostedGamesService.get_welcome_message()
    
    success = await HostedGamesService.safe_edit_message(
        query, 
        welcome_message, 
        keyboard,
        fallback_message="🏠 Main Menu\nWhat would you like to do?"
    )
    
    if not success:
        print("Warning: Both edit and fallback message failed")
    
    return ConversationHandler.END