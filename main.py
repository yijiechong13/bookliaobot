from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ChatMemberHandler
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
from membertracking import track_new_members, track_left_members, track_chat_member_updates, initialize_member_counts
filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)


from joingamehandlers import *
from config import * 
from dotenv import load_dotenv
import os
load_dotenv()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear() 

    keyboard = [
        [InlineKeyboardButton("🏟️ Host a Game", callback_data="host_game")],
        [InlineKeyboardButton("👥 Join a Game", callback_data="join_game")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome = (
        "🎉 Welcome to BookLiao Bot! \nThis bot helps NUS students organise or join casual sports games — anytime, anywhere. \n\n " \
            "Here's how it works:\n"
            "📢 Browse games in @BookLiaoAnnouncementChannel and join via the group links.\n\n"
            "You can also:\n"
            "🏟️ *Host a Game* — Pick a sport, time, venue & skill level for others to join.\n"
            "👥 *Join a Game* — Filter games by your preferences and save them for next time.\n\n"
            "Let’s get started! Choose an option below:"
    )

    if update.message:
        await update.message.reply_text(
            text=welcome,
            reply_markup=reply_markup, 
            parse_mode = 'Markdown'
        )

    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=welcome,
            reply_markup=reply_markup,
            parse_mode = 'Markdown'
        )
    else:
        chat_id = update.effective_chat.id
        await context.bot.send_message(
            chat_id=chat_id,
            text=welcome,
            reply_markup=reply_markup,
            parse_mode = 'Markdown'
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear() 
    reply = "Cancelled. Use /start to begin again"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(reply)
    else:
        await update.effective_message.reply_text(reply)
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    #for errors that are not in the try-except block 
    error = context.error
    error_traceback = "".join(traceback.format_tb(error.__traceback__)) if error else "No traceback"
    
    print(f"❌ Error: {type(error).__name__}: {error}")
    print(f"📋 Traceback:\n{error_traceback}")

    if update is None:
        print("⚠️ Update is None - likely a background job error")
        return
    
    try:
        if update.callback_query:
            await update.callback_query.message.reply_text(
                "⚠️ An error occurred. Please try again or /start"
        )
        elif update.message:
            await update.message.reply_text(
                "⚠️ An error occurred. Please try again or /start"
        )
    except Exception as e:
        print(f"❌ Error in error handler: {e}")
        
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

async def initialize_member_counts_job(context):
    """Initialize member counts for existing games on startup"""
    try:
        print("🔄 Initializing member counts...")
        await initialize_member_counts(context)
        print("✅ Member count initialization completed")
    except Exception as e:
        print(f"❌ Error in member count initialization: {e}")


async def initialize_reminders_job(context):
    try:
        print("⏰ Initializing reminders...")
        reminder_service = context.bot_data['reminder_service']
        await reminder_service.schedule_all_existing_reminders(context)
        print("✅ Reminder initialization completed")
    except Exception as e:
        print(f"❌ Error in reminder initialization: {e}")

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
        traceback.print_exc()
        return

    job_queue = application.job_queue
    
    # Run cleanup every hour
    job_queue.run_repeating(
        cleanup_expired_games,
        interval=timedelta(hours=1),
        first=10  # Start after 10 seconds
    )

    # Initialize reminders for existing games on startup
    job_queue.run_once(
        initialize_reminders_job,
        when=20  # Run 20 seconds after startup
    )

    job_queue.run_once(
        initialize_member_counts_job,
        when=30  # Run 30 seconds after startup
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
            VENUE_CONFIRM: [
                CallbackQueryHandler(venue_confirmation, pattern="^venue_confirm:.*$"),
                CallbackQueryHandler(venue_confirmation, pattern="^venue_original:.*$"),
                CallbackQueryHandler(venue_confirmation, pattern="^venue_retype$")
                ],
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
        conversation_timeout = 300, 
        allow_reentry = True, 
    )

    join_conv = ConversationHandler (
        entry_points=[CallbackQueryHandler(join_game, pattern="^join_game$")],
        states= {
            SETTING_FILTERS: [
                CallbackQueryHandler(handle_filter_selection,pattern="^filter_"),
                CallbackQueryHandler(clear_filters,pattern="^clear_"),
                CallbackQueryHandler(back_to_filters,pattern="^back_to_filters$"),
                CallbackQueryHandler(show_results,pattern="^show_results$"),],
            SETTING_SPORTS: [
                CallbackQueryHandler(toggle_filter,pattern="^toggle_filter_sport_"),
                CallbackQueryHandler(clear_filters,pattern="^clear_sport_filters$"),
                CallbackQueryHandler(apply_filters,pattern="^apply_filters_sport$"),
                CallbackQueryHandler(back_to_filters,pattern="^back_to_filters$"),],
            SETTING_SKILL: [
                CallbackQueryHandler(toggle_filter,pattern="^toggle_filter_skill_"),
                CallbackQueryHandler(clear_filters,pattern="^clear_skill_filters$"),
                CallbackQueryHandler(apply_filters,pattern="^apply_filters_skill$"),
                CallbackQueryHandler(back_to_filters,pattern="^back_to_filters$"),],
            SETTING_DATE: [
                CallbackQueryHandler(toggle_filter,pattern="^toggle_filter_date_"),
                CallbackQueryHandler(clear_filters,pattern="^clear_date_filters$"),
                CallbackQueryHandler(apply_filters,pattern="^apply_filters_date$"),
                CallbackQueryHandler(back_to_filters,pattern="^back_to_filters$"),],
            SETTING_TIME: [
                CallbackQueryHandler(toggle_filter,pattern="^toggle_filter_time_"),
                CallbackQueryHandler(clear_filters,pattern="^clear_time_filters$"),
                CallbackQueryHandler(apply_filters,pattern="^apply_filters_time$"),
                CallbackQueryHandler(back_to_filters,pattern="^back_to_filters$"),],
            SETTING_VENUE:[
                CallbackQueryHandler(toggle_filter,pattern="^toggle_filter_venue_"),
                CallbackQueryHandler(clear_filters,pattern="^clear_venue_filters$"),
                CallbackQueryHandler(apply_filters,pattern="^apply_filters_venue$"),
                CallbackQueryHandler(back_to_filters,pattern="^back_to_filters$"),],
            BROWSE_GAMES: [CallbackQueryHandler(handle_navigation, pattern="^(prev_game|next_game)$"),
                           CallbackQueryHandler(join_selected_game, pattern="^join_selected_"),
                           CallbackQueryHandler(back_to_filters, pattern="^back_to_filters$")]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message = False,
        conversation_timeout = 300, 
        allow_reentry = True, 
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(start, pattern="^start$"))

    application.add_handler(host_conv)
    application.add_handler(join_conv)

     # Handle regular member joins
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        track_new_members
    ))

     # Handle regular member leaves
    application.add_handler(MessageHandler(
        filters.StatusUpdate.LEFT_CHAT_MEMBER,
        track_left_members
    ))

      # Handle admin actions (kicks, bans, promotions)
    application.add_handler(ChatMemberHandler(
        track_chat_member_updates, 
        ChatMemberHandler.CHAT_MEMBER
    ))

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