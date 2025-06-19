##import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, JobQueue
from mainhandlers import *
from hosthandlers import *
from joingamehandlers import *
from config import * 
from dotenv import load_dotenv
import os
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")
from firebase_init import db

def main():
    application = Application.builder().token(TOKEN).build()
    
    host_conv = ConversationHandler (
        entry_points=[CallbackQueryHandler(host_game, pattern="^host_game$")],
        states= {
            ASK_BOOKING: [CallbackQueryHandler(handle_venue_response, pattern="^(venue_yes|venue_no)$")],
            WAITING_BOOKING_CONFIRM: [CallbackQueryHandler(after_booking, pattern="^done_booking$")],
            WAITING_FOR_GROUP_LINK: [CallbackQueryHandler(handle_telegram_group_response, pattern="^(group_yes|group_no)$")], 
            GET_GROUP_LINK: [CallbackQueryHandler(get_group_link)], 
            RECEIVED_GROUP_LINK:[MessageHandler(filters.TEXT & ~filters.COMMAND, receive_group_link)],
            SPORT: [CallbackQueryHandler(sport_chosen)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, time_chosen)],
            VENUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, venue_chosen)],
            SKILL: [CallbackQueryHandler(skill_chosen)],
            CONFIRMATION: [CallbackQueryHandler(save_game, pattern="^confirm_game$"),
                           CallbackQueryHandler(cancel, pattern="^cancel_game$")]
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start)],
        per_message = False,
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
    application.add_handler(CommandHandler('cancel', cancel))

    application.add_handler(host_conv)
    application.add_handler(join_conv)

    application.add_error_handler(error_handler)

    try:
        application.run_polling()
    except Exception as e:
        print(f"Fatal error: {str(e)}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    error = str(context.error)
    print(f"Global error handler caught: {error}")
    
    if update.callback_query:
        try:
            await update.callback_query.message.reply_text(
                "⚠️ An error occurred. Please try again or use /start to restart."
            )
        except:
            pass
    elif update.message:
        await update.message.reply_text(
            "⚠️ An error occurred. Please try again or use /start to restart."
        )

if __name__ == "__main__":
    main()
