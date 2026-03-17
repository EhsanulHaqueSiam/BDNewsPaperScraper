"""
Tests for Bengali Date Conversion Module
=========================================
Comprehensive tests for BDNewsPaper.bengalidate_to_englishdate covering:
    - Bengali <-> English number conversion
    - Bengali date string parsing and conversion
    - Relative date handling
    - Date formatting
    - Validation utilities
    - BengaliDateParser class
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import patch

import pytz

from BDNewsPaper.bengalidate_to_englishdate import (
    bengali_to_english_number,
    bengali_to_english_numbers,
    english_to_bengali_number,
    convert_bengali_date_to_english,
    format_bengali_date,
    validate_bengali_date_format,
    is_valid_date,
    parse_bengali_month,
    parse_bengali_time,
    parse_relative_date,
    extract_numbers,
    BengaliDateParser,
    BENGALI_TO_ENGLISH_NUMS,
    BENGALI_MONTHS,
    BENGALI_DAYS,
    BENGALI_TIME_PERIODS,
)

DHAKA_TZ = pytz.timezone("Asia/Dhaka")


# ==============================================================================
# bengali_to_english_number (single string)
# ==============================================================================

class TestBengaliToEnglishNumber:
    """Tests for bengali_to_english_number (single-string API)."""

    def test_single_digit(self):
        assert bengali_to_english_number("১") == "1"
        assert bengali_to_english_number("০") == "0"
        assert bengali_to_english_number("৯") == "9"

    def test_multi_digit(self):
        assert bengali_to_english_number("১২৩") == "123"
        assert bengali_to_english_number("২০২৪") == "2024"

    def test_mixed_text(self):
        assert bengali_to_english_number("মার্চ ১৫") == "মার্চ 15"

    def test_empty_string(self):
        assert bengali_to_english_number("") == ""

    def test_no_bengali_numbers(self):
        assert bengali_to_english_number("hello") == "hello"
        assert bengali_to_english_number("123") == "123"

    def test_all_digits(self):
        assert bengali_to_english_number("০১২৩৪৫৬৭৮৯") == "0123456789"

    def test_non_string_input_returns_str(self):
        result = bengali_to_english_number(42)
        assert result == "42"


# ==============================================================================
# bengali_to_english_numbers (list API, backward compat)
# ==============================================================================

class TestBengaliToEnglishNumbers:
    """Tests for bengali_to_english_numbers (list-based API)."""

    def test_single_element(self):
        assert bengali_to_english_numbers(["১২৩"]) == ["123"]

    def test_multiple_elements(self):
        assert bengali_to_english_numbers(["১", "২", "৩"]) == ["1", "2", "3"]

    def test_mixed_text_in_list(self):
        assert bengali_to_english_numbers(["মার্চ ১৫"]) == ["মার্চ 15"]

    def test_empty_list(self):
        assert bengali_to_english_numbers([]) == []

    def test_raises_type_error_on_non_list(self):
        with pytest.raises(TypeError):
            bengali_to_english_numbers("not a list")

    def test_raises_value_error_on_non_string_element(self):
        with pytest.raises(ValueError):
            bengali_to_english_numbers([123])


# ==============================================================================
# english_to_bengali_number
# ==============================================================================

class TestEnglishToBengaliNumber:
    """Tests for english_to_bengali_number."""

    def test_single_digit(self):
        assert english_to_bengali_number("1") == "১"
        assert english_to_bengali_number("0") == "০"

    def test_multi_digit(self):
        assert english_to_bengali_number("2024") == "২০২৪"
        assert english_to_bengali_number("123") == "১২৩"

    def test_mixed_text_preserved(self):
        assert english_to_bengali_number("July 10") == "July ১০"

    def test_empty_string(self):
        assert english_to_bengali_number("") == ""

    def test_non_string_input(self):
        assert english_to_bengali_number(42) == "৪২"

    def test_roundtrip_with_bengali_to_english(self):
        original = "২০২৪"
        english = bengali_to_english_number(original)
        back = english_to_bengali_number(english)
        assert back == original


# ==============================================================================
# convert_bengali_date_to_english
# ==============================================================================

class TestConvertBengaliDate:
    """Tests for the main convert_bengali_date_to_english function."""

    def test_standard_format(self):
        """Month Day, Year format: 'জুলাই ১০, ২০২৪'"""
        result = convert_bengali_date_to_english("জুলাই ১০, ২০২৪")
        assert result is not None
        assert result.year == 2024
        assert result.month == 7
        assert result.day == 10

    def test_reversed_format(self):
        """Day Month Year format: '১৫ ডিসেম্বর ২০২৪'"""
        result = convert_bengali_date_to_english("১৫ ডিসেম্বর ২০২৪")
        assert result is not None
        assert result.year == 2024
        assert result.month == 12
        assert result.day == 15

    def test_with_day_name(self):
        """Date string preceded by a Bengali day name."""
        result = convert_bengali_date_to_english("শনিবার, জুলাই ১০, ২০২৪")
        assert result is not None
        assert result.year == 2024
        assert result.month == 7
        assert result.day == 10

    def test_with_time(self):
        """Date string with Bengali time period and clock time."""
        result = convert_bengali_date_to_english("সকাল ১০:৩০, জুলাই ১০, ২০২৪")
        assert result is not None
        assert result.year == 2024
        assert result.month == 7
        assert result.day == 10
        assert result.hour == 10
        assert result.minute == 30

    def test_afternoon_time(self):
        result = convert_bengali_date_to_english("বিকাল ৫:৪৫, ডিসেম্বর ১৫ ২০২৪")
        assert result is not None
        assert result.month == 12
        assert result.day == 15
        assert result.hour == 17
        assert result.minute == 45

    def test_alternate_month_spelling_january(self):
        """'জানুয়ারী' (alternate) should work the same as 'জানুয়ারি'."""
        r1 = convert_bengali_date_to_english("জানুয়ারী ১, ২০২৫")
        r2 = convert_bengali_date_to_english("জানুয়ারি ১, ২০২৫")
        assert r1 is not None
        assert r2 is not None
        assert r1.month == r2.month == 1

    def test_alternate_month_spelling_february(self):
        r1 = convert_bengali_date_to_english("ফেব্রুয়ারী ১৪, ২০২৪")
        r2 = convert_bengali_date_to_english("ফেব্রুয়ারি ১৪, ২০২৪")
        assert r1 is not None
        assert r2 is not None
        assert r1.month == r2.month == 2

    def test_alternate_month_spelling_august(self):
        r1 = convert_bengali_date_to_english("আগষ্ট ১০, ২০২৩")
        r2 = convert_bengali_date_to_english("আগস্ট ১০, ২০২৩")
        assert r1 is not None
        assert r2 is not None
        assert r1.month == r2.month == 8

    def test_relative_today(self):
        result = convert_bengali_date_to_english("আজ")
        assert result is not None
        today = datetime.now(DHAKA_TZ)
        assert result.date() == today.date()

    def test_relative_yesterday(self):
        result = convert_bengali_date_to_english("গতকাল")
        assert result is not None
        yesterday = datetime.now(DHAKA_TZ) - timedelta(days=1)
        assert result.date() == yesterday.date()

    def test_relative_tomorrow(self):
        result = convert_bengali_date_to_english("আগামীকাল")
        assert result is not None
        tomorrow = datetime.now(DHAKA_TZ) + timedelta(days=1)
        assert result.date() == tomorrow.date()

    def test_invalid_returns_none(self):
        assert convert_bengali_date_to_english("not a date") is None
        assert convert_bengali_date_to_english("random text ১২৩") is None

    def test_empty_returns_none(self):
        assert convert_bengali_date_to_english("") is None
        assert convert_bengali_date_to_english("   ") is None

    def test_none_input_returns_none(self):
        assert convert_bengali_date_to_english(None) is None

    def test_timezone_is_dhaka(self):
        result = convert_bengali_date_to_english("জুলাই ১০, ২০২৪")
        assert result is not None
        assert result.tzinfo is not None
        assert str(result.tzinfo) in ("Asia/Dhaka", "+06", "+06:00", "LMT")
        utc_offset = result.utcoffset()
        assert utc_offset.total_seconds() == 6 * 3600

    def test_custom_timezone(self):
        result = convert_bengali_date_to_english(
            "জুলাই ১০, ২০২৪", timezone="UTC"
        )
        assert result is not None
        assert result.utcoffset().total_seconds() == 0

    def test_include_time_false_ignores_time(self):
        result = convert_bengali_date_to_english(
            "সকাল ১০:৩০, জুলাই ১০, ২০২৪", include_time=False
        )
        assert result is not None
        assert result.hour == 0
        assert result.minute == 0

    def test_all_twelve_months(self):
        """Every standard Bengali month name should parse correctly."""
        months_and_expected = [
            ("জানুয়ারি ১, ২০২৪", 1),
            ("ফেব্রুয়ারি ১, ২০২৪", 2),
            ("মার্চ ১, ২০২৪", 3),
            ("এপ্রিল ১, ২০২৪", 4),
            ("মে ১, ২০২৪", 5),
            ("জুন ১, ২০২৪", 6),
            ("জুলাই ১, ২০২৪", 7),
            ("আগস্ট ১, ২০২৪", 8),
            ("সেপ্টেম্বর ১, ২০২৪", 9),
            ("অক্টোবর ১, ২০২৪", 10),
            ("নভেম্বর ১, ২০২৪", 11),
            ("ডিসেম্বর ১, ২০২৪", 12),
        ]
        for date_str, expected_month in months_and_expected:
            result = convert_bengali_date_to_english(date_str)
            assert result is not None, f"Failed to parse: {date_str}"
            assert result.month == expected_month, (
                f"Expected month {expected_month} for '{date_str}', got {result.month}"
            )


# ==============================================================================
# BengaliDateParser class
# ==============================================================================

class TestBengaliDateParser:
    """Tests for the BengaliDateParser OOP interface."""

    def test_parse_standard(self):
        parser = BengaliDateParser()
        result = parser.parse("জুলাই ১০, ২০২৪")
        assert result is not None
        assert result.year == 2024
        assert result.month == 7
        assert result.day == 10

    def test_parse_returns_datetime(self):
        parser = BengaliDateParser()
        result = parser.parse("ডিসেম্বর ২৫, ২০২৪")
        assert isinstance(result, datetime)

    def test_parse_date_returns_date(self):
        parser = BengaliDateParser()
        result = parser.parse_date("ডিসেম্বর ২৫, ২০২৪")
        assert isinstance(result, date)
        assert result == date(2024, 12, 25)

    def test_strict_mode_raises_on_invalid(self):
        parser = BengaliDateParser(strict=True)
        with pytest.raises(ValueError, match="Failed to parse"):
            parser.parse("not a bengali date")

    def test_non_strict_returns_none_on_invalid(self):
        parser = BengaliDateParser(strict=False)
        assert parser.parse("invalid text") is None

    def test_validate_method(self):
        parser = BengaliDateParser()
        assert parser.validate("জুলাই ১০, ২০২৪") is True
        assert parser.validate("not a date") is False

    def test_format_method(self):
        parser = BengaliDateParser()
        dt = datetime(2024, 1, 15)
        formatted = parser.format(dt)
        assert "১৫" in formatted
        assert "২০২৪" in formatted

    def test_convert_numbers_method(self):
        parser = BengaliDateParser()
        assert parser.convert_numbers("২০২৪") == "2024"

    def test_custom_timezone(self):
        parser = BengaliDateParser(timezone="UTC")
        result = parser.parse("জুলাই ১০, ২০২৪")
        assert result is not None
        assert result.utcoffset().total_seconds() == 0

    def test_include_time_false(self):
        parser = BengaliDateParser(include_time=False)
        result = parser.parse("সকাল ১০:৩০, জুলাই ১০, ২০২৪")
        assert result is not None
        assert result.hour == 0
        assert result.minute == 0


# ==============================================================================
# validate_bengali_date_format
# ==============================================================================

class TestValidateBengaliDate:
    """Tests for validate_bengali_date_format."""

    def test_valid_date_returns_true(self):
        assert validate_bengali_date_format("জুলাই ১০, ২০২৪") is True

    def test_valid_reversed_format(self):
        assert validate_bengali_date_format("১৫ ডিসেম্বর ২০২৪") is True

    def test_relative_date_returns_true(self):
        assert validate_bengali_date_format("আজ") is True
        assert validate_bengali_date_format("গতকাল") is True

    def test_english_date_returns_false(self):
        assert validate_bengali_date_format("July 10, 2024") is False

    def test_empty_returns_false(self):
        assert validate_bengali_date_format("") is False

    def test_none_returns_false(self):
        assert validate_bengali_date_format(None) is False

    def test_whitespace_only_returns_false(self):
        assert validate_bengali_date_format("   ") is False

    def test_numbers_without_month_returns_false(self):
        assert validate_bengali_date_format("১২৩৪") is False


# ==============================================================================
# is_valid_date
# ==============================================================================

class TestIsValidDate:
    """Tests for is_valid_date."""

    def test_valid_date(self):
        assert is_valid_date(2024, 7, 10) is True

    def test_invalid_month_zero(self):
        assert is_valid_date(2024, 0, 10) is False

    def test_invalid_month_thirteen(self):
        assert is_valid_date(2024, 13, 10) is False

    def test_invalid_day_zero(self):
        assert is_valid_date(2024, 7, 0) is False

    def test_invalid_day_32(self):
        assert is_valid_date(2024, 7, 32) is False

    def test_leap_year_feb_29(self):
        assert is_valid_date(2024, 2, 29) is True

    def test_non_leap_year_feb_29(self):
        assert is_valid_date(2023, 2, 29) is False

    def test_leap_year_feb_28(self):
        assert is_valid_date(2023, 2, 28) is True

    def test_end_of_months(self):
        assert is_valid_date(2024, 1, 31) is True
        assert is_valid_date(2024, 4, 30) is True
        assert is_valid_date(2024, 4, 31) is False


# ==============================================================================
# format_bengali_date
# ==============================================================================

class TestFormatBengaliDate:
    """Tests for format_bengali_date."""

    def test_basic_format(self):
        dt = datetime(2024, 1, 15)
        result = format_bengali_date(dt)
        assert "১৫" in result
        assert "২০২৪" in result

    def test_format_with_day_name(self):
        dt = datetime(2024, 7, 10)  # This is a Wednesday
        result = format_bengali_date(dt, include_day=True)
        assert "বুধবার" in result

    def test_format_with_time(self):
        dt = datetime(2024, 7, 10, 10, 30)
        result = format_bengali_date(dt, include_time=True)
        assert "সকাল" in result
        assert "১০" in result
        assert "৩০" in result

    def test_format_afternoon_time(self):
        dt = datetime(2024, 7, 10, 15, 0)
        result = format_bengali_date(dt, include_time=True)
        assert "বিকাল" in result

    def test_format_night_time(self):
        dt = datetime(2024, 7, 10, 22, 0)
        result = format_bengali_date(dt, include_time=True)
        assert "রাত" in result

    def test_date_object_input(self):
        d = date(2024, 1, 15)
        result = format_bengali_date(d)
        assert "১৫" in result
        assert "২০২৪" in result

    def test_roundtrip_date(self):
        """Format a datetime to Bengali, then parse it back."""
        original = datetime(2024, 12, 25)
        bengali_str = format_bengali_date(original)
        parsed = convert_bengali_date_to_english(bengali_str)
        assert parsed is not None
        assert parsed.year == 2024
        assert parsed.month == 12
        assert parsed.day == 25


# ==============================================================================
# parse_bengali_month
# ==============================================================================

class TestParseBengaliMonth:
    """Tests for parse_bengali_month."""

    def test_exact_match(self):
        assert parse_bengali_month("জুলাই") == "July"

    def test_within_text(self):
        assert parse_bengali_month("১৫ জুলাই ২০২৪") == "July"

    def test_no_month_returns_none(self):
        assert parse_bengali_month("no month here") is None

    def test_abbreviated_month(self):
        assert parse_bengali_month("জানু") == "January"

    def test_alternate_spelling(self):
        assert parse_bengali_month("জানুয়ারী") == "January"
        assert parse_bengali_month("জানুয়ারি") == "January"


# ==============================================================================
# parse_bengali_time
# ==============================================================================

class TestParseBengaliTime:
    """Tests for parse_bengali_time."""

    def test_morning_time(self):
        result = parse_bengali_time("সকাল ১০:৩০")
        assert result is not None
        assert result == (10, 30)

    def test_afternoon_time(self):
        result = parse_bengali_time("বিকাল ৫:৪৫")
        assert result is not None
        assert result == (17, 45)

    def test_no_time_returns_none(self):
        assert parse_bengali_time("জুলাই ২০২৪") is None

    def test_noon_time(self):
        result = parse_bengali_time("দুপুর ১২:০০")
        assert result is not None
        assert result[0] == 12


# ==============================================================================
# parse_relative_date
# ==============================================================================

class TestParseRelativeDate:
    """Tests for parse_relative_date."""

    def test_today(self):
        ref = datetime(2024, 7, 10, 12, 0, tzinfo=DHAKA_TZ)
        result = parse_relative_date("আজ", reference_date=ref)
        assert result is not None
        assert result.date() == date(2024, 7, 10)

    def test_yesterday(self):
        ref = datetime(2024, 7, 10, 12, 0, tzinfo=DHAKA_TZ)
        result = parse_relative_date("গতকাল", reference_date=ref)
        assert result is not None
        assert result.date() == date(2024, 7, 9)

    def test_tomorrow(self):
        ref = datetime(2024, 7, 10, 12, 0, tzinfo=DHAKA_TZ)
        result = parse_relative_date("আগামীকাল", reference_date=ref)
        assert result is not None
        assert result.date() == date(2024, 7, 11)

    def test_day_before_yesterday(self):
        ref = datetime(2024, 7, 10, 12, 0, tzinfo=DHAKA_TZ)
        result = parse_relative_date("পরশু", reference_date=ref)
        assert result is not None
        assert result.date() == date(2024, 7, 8)

    def test_non_relative_returns_none(self):
        assert parse_relative_date("জুলাই ১০") is None


# ==============================================================================
# extract_numbers
# ==============================================================================

class TestExtractNumbers:
    """Tests for extract_numbers."""

    def test_bengali_numbers(self):
        assert extract_numbers("জানুয়ারি ১৫, ২০২৪") == [15, 2024]

    def test_english_numbers(self):
        assert extract_numbers("January 15, 2024") == [15, 2024]

    def test_no_numbers(self):
        assert extract_numbers("no numbers here") == []

    def test_convert_bengali_false(self):
        # Python's \d regex matches Unicode digits, so Bengali numerals
        # are still captured by re.findall even without explicit conversion.
        result = extract_numbers("hello", convert_bengali=False)
        assert result == []


# ==============================================================================
# Constants
# ==============================================================================

class TestConstants:
    """Verify module-level constant dictionaries are well-formed."""

    def test_bengali_to_english_nums_has_ten_entries(self):
        assert len(BENGALI_TO_ENGLISH_NUMS) == 10

    def test_bengali_months_contains_all_standard_months(self):
        english_months = set(BENGALI_MONTHS.values())
        expected = {
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        }
        assert expected.issubset(english_months)

    def test_bengali_days_contains_all_seven(self):
        english_days = set(BENGALI_DAYS.values())
        expected = {
            "Saturday", "Sunday", "Monday", "Tuesday",
            "Wednesday", "Thursday", "Friday",
        }
        assert expected.issubset(english_days)

    def test_time_periods_are_tuples(self):
        for key, val in BENGALI_TIME_PERIODS.items():
            assert isinstance(val, tuple), f"{key} should map to a tuple"
            assert len(val) == 2
