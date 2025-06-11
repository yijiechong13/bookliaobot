import os
from dotenv import load_dotenv
##import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, JobQueue
from mainhandlers import *
from createagame import *
from cancelagame import *
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from savegame import GameDatabase

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

load_dotenv()

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    application = Application.builder().token(TOKEN).build()

    db = GameDatabase()
    application.bot_data['db'] = db
    
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
            WAITING_FOR_GROUP_LINK: [CallbackQueryHandler(handle_telegram_group_response, pattern="^(group_yes|group_no)$")], 
            GET_GROUP_LINK: [CallbackQueryHandler(get_group_link)], 
            RECEIVED_GROUP_LINK:[MessageHandler(filters.TEXT & ~filters.COMMAND, receive_group_link)],
            SPORT: [CallbackQueryHandler(sport_chosen)],
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
        conversation_timeout = 300, 
        allow_reentry = True, per_chat = True
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('cancel', cancel))
    

    application.add_handler(host_conv)

    application.add_error_handler(error_handler)

    print("Bot is starting...") 
    application.run_polling(
    poll_interval=1,
    drop_pending_updates=True
)   

if __name__ == "__main__":
    main()