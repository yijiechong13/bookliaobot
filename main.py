##import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, JobQueue
from mainhandlers import *
from hosthandlers import *
from joingamehandlers import *
from config import * 
from .env import *

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
        conversation_timeout = 300, 
        allow_reentry = True, 
    )
    
    join_conv = ConversationHandler (
        entry_points=[CallbackQueryHandler(join_game, pattern="^join_game$")],
        states= {
            SPORT: [CallbackQueryHandler(sport_chosen)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, time_chosen)],
            VENUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, venue_chosen)],
            SKILL: [CallbackQueryHandler(skill_chosen)],
            CONFIRMATION: [CallbackQueryHandler(save_game, pattern="^confirm_game$"),
                           CallbackQueryHandler(cancel, pattern="^cancel_game$")],
            SHOWING_RESULTS: [CallbackQueryHandler(handle_navigation, pattern="^(prev_game|next_game)$"),
                              CallbackQueryHandler(join_game, pattern="^(join_selected$"),
                              CallbackQueryHandler(handle_filter_selection, pattern="^(back_to_filters$")]
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start)],
        conversation_timeout = 300, 
        allow_reentry = True, 
    )


    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('cancel', cancel))

    application.add_handler(host_conv)
    application.add_handler(join_conv)

    application.add_error_handler(error_handler)

    application.run_polling(
    poll_interval=1,
    drop_pending_updates=True
)   

if __name__ == "__main__":
    main()
