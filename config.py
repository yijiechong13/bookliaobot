#Conversation states for hosting game
ASK_BOOKING, WAITING_BOOKING_CONFIRM, WAITING_FOR_GROUP_LINK,GET_GROUP_LINK, RECEIVED_GROUP_LINK, SPORT, TIME, VENUE, SKILL, CONFIRMATION = range(10)


#Conversation states for joining games and preference 
SETTING_SPORTS, SETTING_SKILL, SETTING_LOCATION, BROWSE_GAMES, GAMES_DETAILS = range(10, 13)

#Sport options 
sports = ["⚽ Football", "🏀 Basketball", "🎾 Tennis", "🏐 Volleyball"]
SKILL_LEVEL = ["Beginner", "Intermediate", "Advanced", "Any Level"]