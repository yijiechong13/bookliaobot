import os
from dotenv import load_dotenv
##import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, JobQueue
from createagame import *
from hostedgames import *  
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from savegame import GameDatabase
from telethon_service import telethon_service
import asyncio
from datetime import timedelta
from reminder import ReminderService
import traceback

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

load_dotenv()

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

    #for errors that are not in the try-except block 
    error = context.error
    error_traceback = "".join(traceback.format_tb(error.__traceback__)) if error else "No traceback"
    
    print(f"❌ Error: {type(error).__name__}: {error}")
    print(f"📋 Traceback:\n{error_traceback}")
    
    if update.callback_query:
        await update.callback_query.message.reply_text(
            "⚠️ An error occurred. Please try again or /start"
        )
    elif update.message:
        await update.message.reply_text(
            "⚠️ An error occurred. Please try again or /start"
        )
        
async def cleanup_expired_games(context):
    try:
        print("🧹 Running cleanup job...")
        db = context.bot_data['db']
        expired_count = await db.close_expired_games(context) 
        if expired_count > 0: 
            print(f"✅ Cleanup completed: closed {expired_count} expired games")
        else: 
            print("📋 Cleanup completed: no expired games found")
    except Exception as e:
        print(f"❌ Error in cleanup job: {e}") 

async def send_reminder(context):
    try:
        print("⏰ Running reminder check...")
        reminder_service = context.bot_data['reminder_service']
        await reminder_service.send_game_reminders(context)
        print("✅ Reminder check completed")
    except Exception as e:
        print(f"❌ Error in reminder job: {e}")

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        print("❌ BOT_TOKEN not found in environment variables")
        return
        
    application = Application.builder().token(TOKEN).build()

    # Initialize database and services
    try:
        db = GameDatabase()   
        application.bot_data['db'] = db

        reminder = ReminderService(db)
        application.bot_data['reminder_service'] = reminder 
        print("✅ Database and reminder service initialized")
    except Exception as e:
        print(f"❌ Error initializing services: {e}")
        return

    job_queue = application.job_queue
    
    # Run cleanup every hour
    job_queue.run_repeating(
        cleanup_expired_games,
        interval=timedelta(hours=1),
        first=10  # Start after 10 seconds
    )

    # Run reminder check every 30 minutes (fixed from 1 minute)
    job_queue.run_repeating(
        send_reminder, 
        interval=timedelta(minutes=30),
        first=15  # Start after 15 seconds
    )

    print("✅ Scheduled jobs configured")

    async def init_telethon():
        try:
            await telethon_service.initialize()
            print("✅ Telethon service initialized")
        except Exception as e:
            print(f"❌ Error initializing Telethon: {e}")
    
    # Run initialization
    try:
        asyncio.get_event_loop().run_until_complete(init_telethon())
    except Exception as e:
        print(f"❌ Error during initialization: {e}")

    host_conv = ConversationHandler (
        entry_points=[CallbackQueryHandler(host_game, pattern="^host_game$")],
        states= {
            HOST_MENU: [
            CallbackQueryHandler(create_game, pattern="^create_game$"),
            CallbackQueryHandler(view_hosted_games, pattern="^view_hosted_games$"),
            CallbackQueryHandler(back_to_main, pattern="^back_to_main$")
        ],
            ASK_BOOKING: [CallbackQueryHandler(handle_venue_response, pattern="^(venue_yes|venue_no)$")],
            WAITING_BOOKING_CONFIRM: [CallbackQueryHandler(after_booking, pattern="^done_booking$")],
            SPORT: [CallbackQueryHandler(sport_chosen)],
            DATE:[MessageHandler(filters.TEXT & ~filters.COMMAND, date_chosen)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, time_chosen)],
            VENUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, venue_chosen)],
            SKILL: [CallbackQueryHandler(skill_chosen)],
            CONFIRMATION: [CallbackQueryHandler(save_game, pattern="^confirm_game$"),
                           CallbackQueryHandler(cancel, pattern="^cancel_game$")],
            VIEW_HOSTED_GAMES: [
                CallbackQueryHandler(navigate_hosted_games, pattern="^(prev_game|next_game)$"),
                CallbackQueryHandler(cancel_game_prompt, pattern="^cancel_game_prompt$"),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$")
            ],
            CONFIRM_CANCEL: [
                CallbackQueryHandler(confirm_cancel_game, pattern="^confirm_cancel$"),
                CallbackQueryHandler(back_to_list, pattern="^back_to_list$")
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start)],
        conversation_timeout=300, 
        allow_reentry=True, per_chat=True
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('cancel', cancel))
    application.add_handler(host_conv)
    application.add_error_handler(error_handler)
    

    print("🚀 Bot is starting...") 
    try:
        application.run_polling(
            poll_interval=1,
            drop_pending_updates=True
        )   
    except Exception as e:
        print(f"❌ Error running bot: {e}")

if __name__ == "__main__":
    main()