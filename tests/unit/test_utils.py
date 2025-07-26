import pytest
import sys
import os
from unittest.mock import MagicMock
from freezegun import freeze_time

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the actual utils functions directly from their modules
# This bypasses the package import issue
sys.path.insert(0, os.path.join(project_root, 'utils'))
from bot.utils.validation_helper import validate_date_format, parse_time_input, convert_to_24_hour
from bot.utils.datetime_helper import is_game_expired

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
        assert err and "Invalid time format" in err
    
    def test_end_time_before_start_time(self):
        _, err = parse_time_input("4pm-2pm")
        assert err == "End time must be later than start time"

    def test_same_start_and_end_time(self):
        _, err = parse_time_input("3pm-3pm")
        assert err == "End time must be later than start time"

class TestGameExpiration:
    
    @freeze_time("2025-06-15 02:00:00")  # 10:00 AM Singapore = 02:00 UTC
    def test_game_not_expired(self):
        is_expired_result = is_game_expired("15/06/2025", "16:00")
        assert is_expired_result is False
    
    @freeze_time("2025-06-15 10:00:00")  # 6:00 PM Singapore = 10:00 UTC  
    def test_game_expired(self):
        is_expired_result = is_game_expired("15/06/2025", "16:00")
        assert is_expired_result is True
    
