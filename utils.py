import re
from datetime import datetime, time
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


class GroupIdHelper:
    
    @staticmethod
    def normalize_group_id(group_id):
        if isinstance(group_id, str):
            # If it's already a string, check if it's a negative supergroup ID
            if group_id.startswith('-'):
                try:
                    numeric_id = int(group_id)
                    if numeric_id < -1000000000000:
                        # This is a supergroup ID, convert to stored format
                        return str(abs(numeric_id + 1000000000000))
                    else:
                        # Regular negative group ID
                        return str(abs(numeric_id))
                except ValueError:
                    return group_id
            else:
                # Positive string ID
                return group_id
        elif isinstance(group_id, int):
            if group_id < -1000000000000:
                # Supergroup ID format
                return str(abs(group_id + 1000000000000))
            elif group_id < 0:
                # Regular negative group ID
                return str(abs(group_id))
            else:
                # Positive group ID
                return str(group_id)
        else:
            return str(group_id)
    
    @staticmethod
    def to_telegram_format(stored_group_id):
        try:
            if isinstance(stored_group_id, str):
                if stored_group_id.startswith('-'):
                    # Already in correct format
                    return int(stored_group_id)
                else:
                    # Convert stored format to supergroup format
                    numeric_id = int(stored_group_id)
                    return -1000000000000 - numeric_id
            elif isinstance(stored_group_id, int):
                if stored_group_id < 0:
                    # Already in correct format
                    return stored_group_id
                else:
                    # Convert to supergroup format
                    return -1000000000000 - stored_group_id
            else:
                # Fallback
                return int(stored_group_id)
        except (ValueError, TypeError):
            print(f"Warning: Could not convert group ID {stored_group_id}")
            return stored_group_id
    
    @staticmethod
    def get_search_group_id(group_id):
        return GroupIdHelper.normalize_group_id(group_id)
    
    @staticmethod
    def log_group_conversion(original_id, converted_id, operation="conversion"):
        print(f"🔄 Group ID {operation}: {original_id} -> {converted_id}")


class DateTimeHelper:
    
    @staticmethod
    def get_singapore_timezone():
        return pytz.timezone("Asia/Singapore")
    
    @staticmethod
    def get_current_singapore_time():
        sg_tz = DateTimeHelper.get_singapore_timezone()
        return datetime.now(sg_tz)
    
    @staticmethod
    def parse_game_datetime(date_str, time_24_str):
        try:
            day, month, year = map(int, date_str.split("/"))
            hour, minute = map(int, time_24_str.split(":"))
            game_datetime = datetime(year, month, day, hour, minute)
            sg_tz = DateTimeHelper.get_singapore_timezone()
            return sg_tz.localize(game_datetime)
        except Exception as e:
            print(f"Error parsing game datetime: {e}")
            return None
    
    @staticmethod
    def is_game_expired(date_str, end_time_24):
        try:
            game_end = DateTimeHelper.parse_game_datetime(date_str, end_time_24)
            if game_end is None:
                return False
            
            now = DateTimeHelper.get_current_singapore_time()
            return now > game_end
        except Exception as e:
            print(f"Error checking if game expired: {e}")
            return False
    
    @staticmethod
    def format_datetime_display(dt):
        if dt is None:
            return "Unknown"
        return dt.strftime("%d/%m/%Y %I:%M %p")


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
