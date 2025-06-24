#Conversation states - Hosting Flow
(
    HOST_MENU,
    ASK_BOOKING, 
    WAITING_BOOKING_CONFIRM, 
    SPORT, 
    DATE, 
    TIME, 
    VENUE,
    SKILL, 
    CONFIRMATION, 
    VIEW_HOSTED_GAMES, 
    CONFIRM_CANCEL
) = range(11)


#Conversation states for joining games and preference 
(
    SETTING_FILTERS,
    SETTING_SPORTS, 
    SETTING_SKILL, 
    SETTING_DATE,
    SETTING_TIME,
    SETTING_VENUE,
    BROWSE_GAMES, 
)= range(11, 18)


#To Check ! 
RESULTS_PER_PAGE = 5