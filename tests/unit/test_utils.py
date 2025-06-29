import pytest
from datetime import datetime
import pytz
from freezegun import freeze_time
from utils import validate_date_format, parse_time_input, is_game_expired, convert_to_24_hour

class TestDateValidation:

    @freeze_time("2025-06-01")
    def test_valid_date_format(self):
        valid, result = validate_date_format("25/12/2025")
        assert valid is True
        assert result == "25/12/2025"
    
    def test_invalid_date_format(self):
        valid, error = validate_date_format("2024-12-25")
        assert valid is False
        assert "dd/mm/yyyy format" in error
    
    def test_invalid_day_month(self):
        assert not validate_date_format("32/12/2025")[0]
        assert not validate_date_format("25/13/2025")[0]

    @freeze_time("2025-06-01")
    def test_past_date(self):
        valid, error = validate_date_format("01/05/2025")
        assert valid is False
        assert "Date cannot be in the past" in error
    

    @freeze_time("2025-06-01")  
    def test_leap_year_date(self):
        valid, result = validate_date_format("29/02/2028")  # Use future leap year
        assert valid is True
    
class TestTimeParser:
    def test_basic_and_minutes(self):
        res, err = parse_time_input("2:30pm-4:45pm")
        assert err is None and res["start_time_24"] == "14:30" and res["end_time_24"] == "16:45"

    def test_noon_midnight(self):
        noon, _ = parse_time_input("12pm-2pm")
        mid , _ = parse_time_input("12am-2am")
        assert noon["start_time_24"] == "12:00" and mid["start_time_24"] == "00:00"

    def test_invalid_format(self):
        _, err = parse_time_input("2-4")
        assert err and "recognised" in err

class TestGameExpiration:
    
    @freeze_time("2025-06-15 02:00:00")  # 10:00 AM Singapore = 02:00 UTC
    def test_game_not_expired(self):
        is_expired = is_game_expired("15/06/2025", "16:00")
        assert is_expired is False
    
    @freeze_time("2025-06-15 10:00:00")  # 6:00 PM Singapore = 10:00 UTC  
    def test_game_expired(self):
        is_expired = is_game_expired("15/06/2025", "16:00")
        assert is_expired is True
    
class Test24HourConversion:
    def test_am_pm_conversion(self):
        assert convert_to_24_hour(1, "am") == 1
        assert convert_to_24_hour(12, "am") == 0  # midnight
        assert convert_to_24_hour(1, "pm") == 13
        assert convert_to_24_hour(12, "pm") == 12  # noon