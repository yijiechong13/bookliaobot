import re
from datetime import datetime, time
import pytz
from .constants import (
    DATE_FORMAT_REGEX, DATE_FORMAT_EXAMPLE, TIME_PATTERN, SINGAPORE_TIMEZONE,
    MIN_YEAR, MIN_DAY, MAX_DAY, MIN_MONTH, MAX_MONTH, MIN_HOUR_12, MAX_HOUR_12, MIN_MINUTE, MAX_MINUTE
)


def validate_date_format(date_str):
    try: 
        # First check: Does it match the expected format?
        if not re.match(DATE_FORMAT_REGEX, date_str):
            return False, f"Please use dd/mm/yyyy format (e.g., {DATE_FORMAT_EXAMPLE})"
        
        # Parse the components
        parts = date_str.split('/')
        if len(parts) != 3:
            return False, f"Please use dd/mm/yyyy format (e.g., {DATE_FORMAT_EXAMPLE})"
        
        try:
            day, month, year = map(int, parts)
        except ValueError:
            return False, f"Please use dd/mm/yyyy format (e.g., {DATE_FORMAT_EXAMPLE})"

        # Validate ranges before creating datetime object
        if not (MIN_DAY <= day <= MAX_DAY):
            return False, f"Day must be between {MIN_DAY} and {MAX_DAY}"
        if not (MIN_MONTH <= month <= MAX_MONTH):
            return False, f"Month must be between {MIN_MONTH} and {MAX_MONTH}"
        if year < MIN_YEAR:
            return False, f"Year must be {MIN_YEAR} or later"
        
        # Now try to create datetime object to validate if date exists
        try:
            test_date = datetime(year, month, day)
        except ValueError:
            return False, f"Invalid date. Please check your input (e.g., {DATE_FORMAT_EXAMPLE})"

        # Format the standardized date
        standardized_date = f"{day:02d}/{month:02d}/{year}"

        # Check if date is in the past (only after confirming it's a valid date)
        sg_tz = pytz.timezone(SINGAPORE_TIMEZONE)
        today = datetime.now(sg_tz).date()
        if test_date.date() < today: 
            return False, "Date cannot be in the past"
        
        return True, standardized_date

    except Exception as e:
        return False, f"Please use dd/mm/yyyy format (e.g., {DATE_FORMAT_EXAMPLE})"


def parse_time_input(time_str):
    try: 
        time_str = time_str.strip().lower()
        
        match = re.search(TIME_PATTERN, time_str)
        if match:
            start_hour = int(match.group(1))
            start_min = int(match.group(2)) if match.group(2) else 0
            start_period = match.group(3)
            end_hour = int(match.group(4))
            end_min = int(match.group(5)) if match.group(5) else 0
            end_period = match.group(6)

            # Validate hour ranges
            if not (MIN_HOUR_12 <= start_hour <= MAX_HOUR_12) or not (MIN_HOUR_12 <= end_hour <= MAX_HOUR_12):
                return None, f"Hours must be between {MIN_HOUR_12} and {MAX_HOUR_12}"
            
            # Validate minute ranges
            if not (MIN_MINUTE <= start_min <= MAX_MINUTE) or not (MIN_MINUTE <= end_min <= MAX_MINUTE):
                return None, f"Minutes must be between {MIN_MINUTE} and {MAX_MINUTE}"

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


class ValidationHelper:

    @staticmethod
    def validate_required_fields(data, required_fields):
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        return len(missing_fields) == 0, missing_fields
    
    @staticmethod
    def validate_game_data(game_data):
        required_fields = ['sport', 'date', 'time_display', 'venue', 'skill', 'group_link']
        is_valid, missing_fields = ValidationHelper.validate_required_fields(game_data, required_fields)
        
        errors = []
        if missing_fields:
            errors.append(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Additional validation
        if 'date' in game_data:
            date_valid, date_error = validate_date_format(game_data['date'])
            if not date_valid:
                errors.append(f"Date validation error: {date_error}")
        
        return len(errors) == 0, errors
    