#Conversation states - Hosting Flow
(
    ASK_BOOKING, 
    WAITING_BOOKING_CONFIRM, 
    WAITING_FOR_GROUP_LINK,
    GET_GROUP_LINK, 
    RECEIVED_GROUP_LINK, 
    SPORT, 
    TIME, 
    VENUE,
    SKILL, 
    CONFIRMATION
) = range(10)


#Conversation states for joining games and preference 
(
    SETTING_FILTERS,
    SETTING_SPORTS, 
    SETTING_SKILL, 
    SETTING_DATE,
    SETTING_TIME,
    SETTING_VENUE,
    BROWSE_GAMES, 
)= range(10, 17)

RESULTS_PER_PAGE = 5
