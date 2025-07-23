import re
from datetime import datetime, time
import pytz


import re
from datetime import datetime
import pytz


def validate_date_format(date_str): 
    try: 
        # First check: Does it match the expected format?
        if not re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_str):
            return False, "Please use dd/mm/yyyy format (e.g., 25/12/2025)"
        
        # Parse the components
        parts = date_str.split('/')
        if len(parts) != 3:
            return False, "Please use dd/mm/yyyy format (e.g., 25/12/2025)"
        
        try:
            day, month, year = map(int, parts)
        except ValueError:
            return False, "Please use dd/mm/yyyy format (e.g., 25/12/2025)"

        # Validate ranges before creating datetime object
        if not (1 <= day <= 31):
            return False, "Day must be between 1 and 31"
        if not (1 <= month <= 12):
            return False, "Month must be between 1 and 12"
        if year < 2025:
            return False, "Year must be 2025 or later"
        
        # Now try to create datetime object to validate if date exists
        try:
            test_date = datetime(year, month, day)
        except ValueError:
            return False, "Invalid date. Please check your input (e.g., 25/12/2025)"

        # Format the standardized date
        standardized_date = f"{day:02d}/{month:02d}/{year}"

        # Check if date is in the past (only after confirming it's a valid date)
        sg_tz = pytz.timezone("Asia/Singapore")
        today = datetime.now(sg_tz).date()
        if test_date.date() < today: 
            return False, "Date cannot be in the past"
        
        return True, standardized_date

    except Exception as e:
        return False, "Please use dd/mm/yyyy format (e.g., 25/12/2025)"
    
def parse_time_input(time_str):

    try: 
        time_str = time_str.strip().lower()

        time_pattern = r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*-\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)' 
    
        match = re.search(time_pattern, time_str)
        if match:
            start_hour = int(match.group(1))
            start_min = int(match.group(2)) if match.group(2) else 0
            start_period = match.group(3)
            end_hour = int(match.group(4))
            end_min = int(match.group(5)) if match.group(5) else 0
            end_period = match.group(6)

            # Validate hour ranges
            if not (1 <= start_hour <= 12) or not (1 <= end_hour <= 12):
                return None, "Hours must be between 1 and 12"
            
            # Validate minute ranges
            if not (0 <= start_min <= 59) or not (0 <= end_min <= 59):
                return None, "Minutes must be between 0 and 59"

            # Convert to 24-hour format
            start_24 = convert_to_24_hour(start_hour, start_period)
            end_24 = convert_to_24_hour(end_hour, end_period)
            
            if start_24 is None or end_24 is None:
                return None, "Invalid time format"
            
            # Create time objects for comparison
            start_time = time(start_24, start_min)
            end_time = time(end_24, end_min)

              # Validate that end time is after start time
            if end_time <= start_time:
                return None, "End time must be later than start time"
                  
            return {
                "original_input": time_str,
                "start_time_24": f"{start_24:02d}:{start_min:02d}",
                "end_time_24": f"{end_24:02d}:{end_min:02d}",
                "display_format": f"{start_hour}{':{:02d}'.format(start_min) if start_min else ''}{start_period}-{end_hour}{':{:02d}'.format(end_min) if end_min else ''}{end_period}"
            }, None
        
        else:
            return None, "Invalid time format"
        
    except Exception as e:
        return None, f"Error parsing time: {str(e)}"


def convert_to_24_hour(hour, period):
    try:
        if period == 'am':
            return 0 if hour == 12 else hour
        else:  # pm
            return 12 if hour == 12 else hour + 12
    except:
        return None

def is_game_expired(date_str, end_time_24):  

    try:
        day, month, year = map(int, date_str.split("/"))

        end_hour, end_min = map(int, end_time_24.split(":"))

        game_end = datetime(year, month, day, end_hour, end_min)

        sg_tz = pytz.timezone("Asia/Singapore")
        game_end = sg_tz.localize(game_end)

        now = datetime.now(sg_tz)

        return now > game_end 
    
    except Exception as e: 
        print(f"Error checking expiration: {e}")
        return False
    



