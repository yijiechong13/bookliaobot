import re
import dateparser
from datetime import datetime, timedelta
import pytz

def parse_time_input(time_str):
    try:
        sg_tz = pytz.timezone('Asia/Singapore')
        
        time_pattern = r"(\d{1,2})\s*(am|pm)\s*-\s*(\d{1,2})\s*(am|pm)"
        time_match = re.search(time_pattern, time_str.lower())
        
        if not time_match:
            return None
            
        date_str = re.sub(time_pattern, '', time_str.lower()).strip()
        
        settings = {
            'TIMEZONE': 'Asia/Singapore',
            'RETURN_AS_TIMEZONE_AWARE': True,
            'PREFER_DATES_FROM': 'future',  
            'RELATIVE_BASE': datetime.now(sg_tz)
        }
        
        # Parse the date
        parsed_date = dateparser.parse(date_str, settings=settings)
        
        if not parsed_date:
            return None
            
        target_date = parsed_date.date()
        
        
        start_hour = int(time_match.group(1))
        start_period = time_match.group(2)
        end_hour = int(time_match.group(3))
        end_period = time_match.group(4)
        
    
        if start_period == 'pm' and start_hour != 12:
            start_hour += 12
        elif start_period == 'am' and start_hour == 12:
            start_hour = 0
            
        if end_period == 'pm' and end_hour != 12:
            end_hour += 12
        elif end_period == 'am' and end_hour == 12:
            end_hour = 0
        
        # Create datetime objects
        start_datetime = sg_tz.localize(
            datetime.combine(target_date, datetime.min.time().replace(hour=start_hour))
        )
        end_datetime = sg_tz.localize(
            datetime.combine(target_date, datetime.min.time().replace(hour=end_hour))
        )

        return {
            "start": start_datetime,
            "end": end_datetime,
            "date_str": get_date_str(target_date, datetime.now(sg_tz))
        }
        
    except Exception as e:
        print(f"Error parsing time: {e}")
        return None

def get_date_str(target_date, now):
    """Convert date into string representation"""
    if target_date == now.date():
        return "today"
    elif target_date == (now + timedelta(days=1)).date():
        return "tomorrow"
    else:
        return target_date.strftime("%A")


def parse_location(venue_str):
    venue_lower = venue_str.lower()
    
    location_keywords = {
        "utown": ["utown", "university town", "ut", "utown field", "utown court"],
        "src": ["src", "sports recreation center", "sports center"],
        "tembusu": ["tembusu", "tem", "tembusu court"],
        "rvrc": ["rvrc", "ridge view", "ridgeview"],
        "capt": ["capt", "college of alice and peter tan"],
        "kent_ridge": ["kent ridge", "kr", "kent ridge common"],
        "pgp": ["pgp", "prince george park", "prince george's park"],
        "computing": ["computing", "com", "comp", "school of computing"],
        "engineering": ["engineering", "eng", "faculty of engineering"],
        "arts": ["arts", "fass", "faculty of arts"],
        "nus": ["nus", "national university"]
    }
    
    for location, keywords in location_keywords.items():
        if any(keyword in venue_lower for keyword in keywords):
            return location
    
    first_word = venue_str.split()[0].lower()
    return first_word if first_word else "other"

if __name__ == "__main__":
    test_cases = [
        "today 2pm-4pm",
        "tomorrow 9am-11am", 
        "monday 3pm-5pm",
        "Dec 25 10am-12pm",
        "25/12 1pm-3pm",
        "next friday 7pm-9pm"
    ]
    
    for test in test_cases:
        result = parse_time_input(test)
        print(f"'{test}' -> {result}")