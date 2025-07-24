import pytz
from datetime import datetime


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


# Standalone function for backward compatibility
def is_game_expired(date_str, end_time_24):
    return DateTimeHelper.is_game_expired(date_str, end_time_24)