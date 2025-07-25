SPORTS_LIST = [
    ("⚽ Football", "Football"),
    ("🏀 Basketball", "Basketball"),
    ("🎾 Tennis", "Tennis"),
    ("🏐 Volleyball", "Volleyball"),
    ("🏸 Badminton", "Badminton"),
    ("🥏 Ultimate Frisbee", "Ultimate Frisbee"),
    ("🏑 Floorball", "Floorball"),
    ("🏓 Table Tennis", "Table Tennis"),
    ("🏉 Touch Rugby", "Touch Rugby")
]

SPORT_EMOJIS = {
    "football": "⚽",
    "basketball": "🏀",
    "tennis": "🎾",
    "volleyball": "🏐",
    "badminton": "🏸",
    "ultimate frisbee": "🥏",
    "floorball": "🏑",
    "table tennis": "🏓",
    "touch rugby": "🏉"
}

VENUES = {
    "Raffles Hall": ["RH", "Raffles"],
    "Kent Ridge Hall": ["KRH", "Kent Ridge"],
    "Temasek Hall": ["TH", "Temasek"],
    "Eusoff Hall": ["EH", "Eusoff"],
    "Sheares Hall": ["SH", "Sheares"],
    "King Edward VII Hall": ["KEVII", "KE7", "King Edward"],
    "Ridge View Residential College": ["RVRC", "Ridge View"],
    "Cinnamon College": ["Cinnamon", "USC College"],
    "Tembusu College": ["Tembusu", "RC4"],
    "College of Alice & Peter Tan": ["CAPT", "Alice Peter"],
    "Residential College 4": ["RC4"],
    "University Town Sports Hall": ["UTSH", "UTown"],
    "Multi-Purpose Sports Hall": ["MPSH"],
    
    
    # ActiveSG Facilities
    "Jurong East Sports Centre": ["JESC", "Jurong East", "JE Sports"],
    "Queenstown Sports Centre": ["QTSC", "Queenstown", "Queenstown Sports"],
    "Bishan Sports Hall": ["BSH", "Bishan", "Bishan Sports"],
    "Toa Payoh Sports Hall": ["TPSH", "Toa Payoh", "TP Sports"],
    "Bedok Sports Centre": ["BSC", "Bedok", "Bedok Sports"],
    "Pasir Ris Sports Centre": ["PRSC", "Pasir Ris", "PR Sports"],
    "Tampines Sports Centre": ["TSC", "Tampines", "Tampines Sports"],
    "Serangoon Sports Centre": ["SSC", "Serangoon", "Serangoon Sports"],
    "Clementi Sports Centre": ["CSC", "Clementi", "Clementi Sports"],
    "Bukit Gombak Sports Centre": ["BGSC", "Bukit Gombak", "BG Sports"],
    "Yio Chu Kang Sports Centre": ["YCKSC", "YCK", "Yio Chu Kang"],
    "Sengkang Sports Centre": ["SKSC", "Sengkang", "SK Sports"],
    "Hougang Sports Centre": ["HSC", "Hougang", "Hougang Sports"],
    "Woodlands Sports Centre": ["WSC", "Woodlands", "Woodlands Sports"],
    "Choa Chu Kang Sports Centre": ["CCKSC", "CCK", "Choa Chu Kang"],
    "Yishun Sports Centre": ["YSC", "Yishun", "Yishun Sports"],
    "Kallang Tennis Centre": ["KTC", "Kallang Tennis"],
    "Kallang Squash Centre": ["KSC", "Kallang Squash"],
    "Jalan Besar Stadium": ["JBS", "Jalan Besar"],
    "Our Tampines Hub": ["OTH", "Tampines Hub"],
    "OCBC Arena": ["OCBC", "Sports Hub Arena"],
    "Singapore Sports Hub": ["SSH", "Sports Hub", "National Stadium"],
    
    # Other Public Facilities
    "Farrer Park Swimming Complex": ["Farrer Park", "Farrer Pool"],
    "Queenstown Swimming Complex": ["Queenstown Pool", "QT Pool"],
    "Jalan Besar Swimming Complex": ["Jalan Besar Pool", "JB Pool"]
}

# Skill levels
SKILL_LEVELS = ["Beginner", "Intermediate", "Advanced"]

# Booking URLs
BOOKING_URLS = {
    'NUS_FACILITIES': "https://reboks.nus.edu.sg/nus_public_web/public/facilities",
    'ACTIVESG': "https://activesg.gov.sg/activities/list"
}



# Conversation states - Hosting Flow
(
    HOST_MENU,
    ASK_BOOKING, 
    WAITING_BOOKING_CONFIRM, 
    SPORT, 
    DATE, 
    TIME, 
    VENUE,
    VENUE_CONFIRM,
    SKILL, 
    CONFIRMATION, 
    VIEW_HOSTED_GAMES, 
    CONFIRM_CANCEL
) = range(12)

# Conversation states for joining games and preferences 
(
    SETTING_FILTERS,
    SETTING_SPORTS, 
    SETTING_SKILL, 
    SETTING_DATE,
    SETTING_TIME,
    SETTING_VENUE,
    BROWSE_GAMES, 
) = range(12, 19)

# Timezone
SINGAPORE_TIMEZONE = "Asia/Singapore"

# Date format patterns
DATE_FORMAT_REGEX = r'^\d{1,2}/\d{1,2}/\d{4}$'
DATE_FORMAT_EXAMPLE = "25/12/2025"

# Time format patterns
TIME_PATTERN = r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*-\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)'

# Telegram supergroup ID offset
TELEGRAM_SUPERGROUP_OFFSET = 1000000000000

# Validation ranges
MIN_YEAR = 2025
MIN_DAY = 1
MAX_DAY = 31
MIN_MONTH = 1
MAX_MONTH = 12
MIN_HOUR_12 = 1
MAX_HOUR_12 = 12
MIN_MINUTE = 0
MAX_MINUTE = 59
