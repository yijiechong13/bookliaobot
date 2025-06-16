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

        return {
            "date": str(target_date),
            "start_time": f"{start_hour:02d}:00",
            "end_time":  f"{end_hour:02d}:00"
            
        }
        
    except Exception as e:
        print(f"Error parsing time: {e}")
        return None
