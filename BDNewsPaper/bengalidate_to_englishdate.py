"""
Bengali Date Converter Module
=============================
Comprehensive utility for converting Bengali dates, numbers, and time formats
to English equivalents with timezone support.

Features:
    - Bengali to English number conversion (০-৯ → 0-9)
    - Bengali month name conversion (জানুয়ারি → January)
    - Bengali day name conversion (শনিবার → Saturday)
    - Multiple date format support (with/without comma, time, relative dates)
    - Relative date parsing ("আজ", "গতকাল", "আগামীকাল")
    - Time parsing ("সকাল ১০:৩০", "বিকাল ৫:৪৫")
    - Timezone-aware datetime conversion
    - Robust error handling with detailed logging
    - Backward compatibility with existing API

Usage:
    >>> from BDNewsPaper.bengalidate_to_englishdate import convert_bengali_date_to_english
    >>> dt = convert_bengali_date_to_english("জুলাই ১০, ২০২৪")
    >>> print(dt)  # 2024-07-10 00:00:00+06:00

    >>> from BDNewsPaper.bengalidate_to_englishdate import BengaliDateParser
    >>> parser = BengaliDateParser()
    >>> parser.parse("১৫ ডিসেম্বর ২০২৪, সকাল ১০:৩০")
"""

import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Union

import pytz

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Bengali to English Mappings
# =============================================================================

# Bengali numerals (০-৯) to English (0-9)
BENGALI_TO_ENGLISH_NUMS: Dict[str, str] = {
    '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4',
    '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'
}

# Reverse mapping: English to Bengali
ENGLISH_TO_BENGALI_NUMS: Dict[str, str] = {v: k for k, v in BENGALI_TO_ENGLISH_NUMS.items()}

# Bengali month names to English
BENGALI_MONTHS: Dict[str, str] = {
    # Full names
    'জানুয়ারি': 'January',
    'জানুয়ারী': 'January',  # Alternate spelling
    'ফেব্রুয়ারি': 'February',
    'ফেব্রুয়ারী': 'February',
    'মার্চ': 'March',
    'এপ্রিল': 'April',
    'মে': 'May',
    'জুন': 'June',
    'জুলাই': 'July',
    'আগস্ট': 'August',
    'আগষ্ট': 'August',  # Alternate spelling
    'সেপ্টেম্বর': 'September',
    'অক্টোবর': 'October',
    'নভেম্বর': 'November',
    'ডিসেম্বর': 'December',
    
    # Abbreviated forms
    'জানু': 'January',
    'ফেব্রু': 'February',
    'ফেব': 'February',
    'মার্': 'March',
    'এপ্রি': 'April',
    'জুলা': 'July',
    'আগ': 'August',
    'সেপ্টে': 'September',
    'সেপ্ট': 'September',
    'অক্টো': 'October',
    'নভে': 'November',
    'ডিসে': 'December',
}

# Bengali day names to English
BENGALI_DAYS: Dict[str, str] = {
    'শনিবার': 'Saturday',
    'রবিবার': 'Sunday',
    'সোমবার': 'Monday',
    'মঙ্গলবার': 'Tuesday',
    'বুধবার': 'Wednesday',
    'বৃহস্পতিবার': 'Thursday',
    'শুক্রবার': 'Friday',
    
    # Short forms
    'শনি': 'Saturday',
    'রবি': 'Sunday',
    'সোম': 'Monday',
    'মঙ্গল': 'Tuesday',
    'বুধ': 'Wednesday',
    'বৃহঃ': 'Thursday',
    'বৃহস্পতি': 'Thursday',
    'শুক্র': 'Friday',
}

# Bengali relative date terms
BENGALI_RELATIVE_DATES: Dict[str, int] = {
    'আজ': 0,           # Today
    'আজকে': 0,         # Today (colloquial)
    'গতকাল': -1,       # Yesterday
    'গতকালকে': -1,     # Yesterday (colloquial)
    'পরশু': -2,        # Day before yesterday
    'আগামীকাল': 1,     # Tomorrow
    'আগামি': 1,        # Tomorrow (short)
    'পরশুদিন': 2,      # Day after tomorrow
}

# Bengali time period prefixes
BENGALI_TIME_PERIODS: Dict[str, Tuple[int, int]] = {
    'সকাল': (6, 0),      # Morning: add 0 hours (AM)
    'সকালে': (6, 0),     # In the morning
    'দুপুর': (12, 0),    # Noon
    'দুপুরে': (12, 0),   # At noon
    'বিকাল': (15, 0),    # Afternoon: 3 PM base
    'বিকেল': (15, 0),    # Afternoon (alternate spelling)
    'বিকালে': (15, 0),   # In the afternoon
    'সন্ধ্যা': (18, 0),  # Evening: 6 PM
    'সন্ধ্যায়': (18, 0), # In the evening
    'রাত': (20, 0),      # Night: 8 PM
    'রাতে': (20, 0),     # At night
    'রাত্রি': (20, 0),   # Night (formal)
    'মধ্যরাত': (0, 0),   # Midnight
}

# Bangla Calendar months (for future extension)
BANGLA_CALENDAR_MONTHS: Dict[str, int] = {
    'বৈশাখ': 1,    # Boishakh (Apr-May)
    'জ্যৈষ্ঠ': 2,  # Joishtho (May-Jun)
    'আষাঢ়': 3,    # Asharh (Jun-Jul)
    'শ্রাবণ': 4,   # Shrabon (Jul-Aug)
    'ভাদ্র': 5,    # Bhadro (Aug-Sep)
    'আশ্বিন': 6,   # Ashwin (Sep-Oct)
    'কার্তিক': 7,  # Kartik (Oct-Nov)
    'অগ্রহায়ণ': 8, # Ogrohayon (Nov-Dec)
    'পৌষ': 9,      # Poush (Dec-Jan)
    'মাঘ': 10,     # Magh (Jan-Feb)
    'ফাল্গুন': 11, # Falgun (Feb-Mar)
    'চৈত্র': 12,   # Choitro (Mar-Apr)
}


# =============================================================================
# Number Conversion Functions
# =============================================================================

def bengali_to_english_number(text: str) -> str:
    """
    Convert Bengali numerals to English numerals in a string.
    
    Args:
        text: String containing Bengali numerals
        
    Returns:
        String with Bengali numerals converted to English
        
    Example:
        >>> bengali_to_english_number("১২৩৪৫")
        '12345'
        >>> bengali_to_english_number("২০২৪")
        '2024'
    """
    if not isinstance(text, str):
        return str(text)
    
    return ''.join(BENGALI_TO_ENGLISH_NUMS.get(char, char) for char in text)


def english_to_bengali_number(text: str) -> str:
    """
    Convert English numerals to Bengali numerals in a string.
    
    Args:
        text: String containing English numerals
        
    Returns:
        String with English numerals converted to Bengali
        
    Example:
        >>> english_to_bengali_number("12345")
        '১২৩৪৫'
    """
    if not isinstance(text, str):
        text = str(text)
    
    return ''.join(ENGLISH_TO_BENGALI_NUMS.get(char, char) for char in text)


def bengali_to_english_numbers(text_list: List[str]) -> List[str]:
    """
    Convert Bengali numerals to English numerals in a list of strings.
    Maintained for backward compatibility.
    
    Args:
        text_list: List of strings containing Bengali numerals
        
    Returns:
        List of strings with Bengali numerals converted to English
        
    Raises:
        TypeError: If input is not a list
        ValueError: If list contains non-string elements
    """
    if not isinstance(text_list, list):
        raise TypeError("Input must be a list")
    
    converted_nums = []
    for text in text_list:
        if not isinstance(text, str):
            raise ValueError(f"All elements must be strings, got {type(text)}")
        converted_nums.append(bengali_to_english_number(text))
    
    return converted_nums


def extract_numbers(text: str, convert_bengali: bool = True) -> List[int]:
    """
    Extract all numbers from a string.
    
    Args:
        text: String containing numbers (Bengali or English)
        convert_bengali: If True, convert Bengali numerals first
        
    Returns:
        List of integers found in the string
        
    Example:
        >>> extract_numbers("জানুয়ারি ১৫, ২০২৪")
        [15, 2024]
    """
    if convert_bengali:
        text = bengali_to_english_number(text)
    
    numbers = re.findall(r'\d+', text)
    return [int(n) for n in numbers]


# =============================================================================
# Date Validation Functions  
# =============================================================================

def validate_bengali_date_format(bengali_date: str) -> bool:
    """
    Validate Bengali date string format.
    
    Args:
        bengali_date: Bengali date string to validate
        
    Returns:
        True if format appears valid, False otherwise
    """
    if not isinstance(bengali_date, str) or not bengali_date.strip():
        return False
    
    # Check for presence of Bengali month
    has_month = any(month in bengali_date for month in BENGALI_MONTHS.keys())
    
    # Check for presence of Bengali or English numbers
    has_numbers = bool(re.search(r'[০-৯0-9]', bengali_date))
    
    # Check for relative date terms
    is_relative = any(term in bengali_date for term in BENGALI_RELATIVE_DATES.keys())
    
    return (has_month and has_numbers) or is_relative


def is_valid_date(year: int, month: int, day: int) -> bool:
    """
    Check if the given date components form a valid date.
    
    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)
        day: Day (1-31)
        
    Returns:
        True if valid date, False otherwise
    """
    try:
        datetime(year, month, day)
        return True
    except ValueError:
        return False


# =============================================================================
# Date Parsing Functions
# =============================================================================

def parse_bengali_month(text: str) -> Optional[str]:
    """
    Find and convert Bengali month name to English.
    
    Args:
        text: String that may contain a Bengali month name
        
    Returns:
        English month name or None if not found
    """
    text = text.strip()
    
    # Try exact match first
    if text in BENGALI_MONTHS:
        return BENGALI_MONTHS[text]
    
    # Try finding month in text
    for bengali, english in BENGALI_MONTHS.items():
        if bengali in text:
            return english
    
    return None


def parse_bengali_day(text: str) -> Optional[str]:
    """
    Find and convert Bengali day name to English.
    
    Args:
        text: String that may contain a Bengali day name
        
    Returns:
        English day name or None if not found
    """
    for bengali, english in BENGALI_DAYS.items():
        if bengali in text:
            return english
    return None


def parse_bengali_time(text: str) -> Optional[Tuple[int, int]]:
    """
    Parse Bengali time string.
    
    Args:
        text: String that may contain Bengali time (e.g., "সকাল ১০:৩০")
        
    Returns:
        Tuple of (hour, minute) or None if not found
    """
    # Convert Bengali numbers first
    converted = bengali_to_english_number(text)
    
    # Try to find time period
    base_hour = 0
    for period, (hour_offset, _) in BENGALI_TIME_PERIODS.items():
        if period in text:
            base_hour = hour_offset
            break
    
    # Find time pattern (HH:MM or HH.MM or just HH টা)
    time_patterns = [
        r'(\d{1,2})[:\.](\d{2})',           # HH:MM or HH.MM
        r'(\d{1,2})\s*টা\s*(\d{1,2})\s*মিনিট',  # X টা Y মিনিট
        r'(\d{1,2})\s*টা',                   # X টা (just hours)
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, converted)
        if match:
            groups = match.groups()
            hour = int(groups[0])
            minute = int(groups[1]) if len(groups) > 1 and groups[1] else 0
            
            # Adjust for time period if hour is less than 12
            if hour < 12 and base_hour >= 12:
                hour += 12
            elif hour == 12 and base_hour < 12:
                hour = 0
            
            # Clamp values
            hour = hour % 24
            minute = min(minute, 59)
            
            return (hour, minute)
    
    return None


def parse_relative_date(text: str, reference_date: Optional[datetime] = None) -> Optional[datetime]:
    """
    Parse relative Bengali date terms.
    
    Args:
        text: String containing relative date (e.g., "আজ", "গতকাল")
        reference_date: Reference date to calculate from (default: now)
        
    Returns:
        Datetime object or None if not a relative date
    """
    if reference_date is None:
        reference_date = datetime.now(pytz.timezone('Asia/Dhaka'))
    
    for term, days_offset in BENGALI_RELATIVE_DATES.items():
        if term in text:
            target_date = reference_date + timedelta(days=days_offset)
            
            # Try to parse time if present
            time_tuple = parse_bengali_time(text)
            if time_tuple:
                target_date = target_date.replace(hour=time_tuple[0], minute=time_tuple[1])
            
            return target_date
    
    return None


def parse_bengali_date_components(bengali_date: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse Bengali date string into components.
    
    Args:
        bengali_date: Bengali date string
        
    Returns:
        Tuple of (month, day, year) or (None, None, None) if parsing fails
        
    Supports formats:
        - "মাস দিন, বছর" (Month Day, Year)
        - "দিন মাস বছর" (Day Month Year)
        - "দিন মাস, বছর" (Day Month, Year)
        - "মাস দিন বছর" (Month Day Year)
    """
    try:
        cleaned = bengali_date.strip()
        
        # Remove day names if present
        for day_bn in BENGALI_DAYS.keys():
            cleaned = cleaned.replace(day_bn, '').strip()
        
        # Remove time components for date parsing
        for period in BENGALI_TIME_PERIODS.keys():
            if period in cleaned:
                # Find and remove time portion
                cleaned = re.sub(rf'{period}\s*[\d০-৯:\.]+\s*(টা|মিনিট)?', '', cleaned).strip()
        
        # Remove common separators and extra spaces
        cleaned = re.sub(r'[,،|/\-]+', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Convert Bengali numbers to English for easier parsing
        converted = bengali_to_english_number(cleaned)
        
        # Find month
        month_english = None
        month_bengali = None
        for bn_month, en_month in BENGALI_MONTHS.items():
            if bn_month in cleaned:
                month_english = en_month
                month_bengali = bn_month
                break
        
        if not month_english:
            return None, None, None
        
        # Extract numbers
        numbers = re.findall(r'\d+', converted)
        
        if len(numbers) < 2:
            return None, None, None
        
        # Determine day and year based on value (year should be >31)
        if len(numbers) == 2:
            if int(numbers[0]) > 31:
                year, day = numbers[0], numbers[1]
            elif int(numbers[1]) > 31:
                day, year = numbers[0], numbers[1]
            else:
                # Assume format: Day Year (small number first)
                day, year = numbers[0], numbers[1]
        else:
            # Three or more numbers - take first as day, last as year
            day = numbers[0]
            year = numbers[-1]
        
        # Validate
        if int(year) < 1900 or int(year) > 2100:
            # Try swapping if year looks like a day
            if int(day) >= 1900 and int(day) <= 2100:
                day, year = year, day
        
        return month_english, day, year
        
    except Exception as e:
        logger.debug(f"Error parsing Bengali date components: {e}")
        return None, None, None


# =============================================================================
# Main Conversion Functions
# =============================================================================

def convert_bengali_date_to_english(
    bengali_date: str, 
    timezone: str = 'Asia/Dhaka',
    include_time: bool = True
) -> Optional[datetime]:
    """
    Convert Bengali date string to timezone-aware English datetime object.
    
    This is the main function for date conversion. It handles various formats
    including dates with times, relative dates, and different ordering.
    
    Args:
        bengali_date: Bengali date string (e.g., "জুলাই ১০, ২০২৪", "১৫ ডিসেম্বর ২০২৪")
        timezone: Target timezone (default: 'Asia/Dhaka')
        include_time: If True, try to parse time from the string
        
    Returns:
        Timezone-aware datetime object or None if conversion fails
        
    Examples:
        >>> convert_bengali_date_to_english("জুলাই ১০, ২০২৪")
        datetime.datetime(2024, 7, 10, 0, 0, tzinfo=<DstTzInfo 'Asia/Dhaka' +06+6:00:00 STD>)
        
        >>> convert_bengali_date_to_english("১৫ ডিসেম্বর ২০২৪, সকাল ১০:৩০")
        datetime.datetime(2024, 12, 15, 10, 30, tzinfo=<DstTzInfo 'Asia/Dhaka' +06+6:00:00 STD>)
        
        >>> convert_bengali_date_to_english("গতকাল")  # Yesterday
        # Returns yesterday's date
    """
    if not bengali_date or not isinstance(bengali_date, str):
        logger.debug("Invalid input: Bengali date must be a non-empty string")
        return None
    
    bengali_date = bengali_date.strip()
    
    if not bengali_date:
        return None
    
    try:
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        logger.error(f"Unknown timezone: {timezone}")
        tz = pytz.timezone('Asia/Dhaka')
    
    # Try relative date first
    relative_result = parse_relative_date(bengali_date)
    if relative_result:
        if relative_result.tzinfo is None:
            return tz.localize(relative_result)
        return relative_result
    
    # Parse date components
    month_english, day_str, year_str = parse_bengali_date_components(bengali_date)
    
    if not all([month_english, day_str, year_str]):
        logger.debug(f"Failed to parse Bengali date components from: {bengali_date}")
        return None
    
    try:
        day = int(day_str)
        year = int(year_str)
        
        # Convert month name to number
        month_to_num = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8,
            'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        month = month_to_num.get(month_english)
        
        if not month:
            logger.error(f"Invalid month: {month_english}")
            return None
        
        # Validate date
        if not is_valid_date(year, month, day):
            logger.error(f"Invalid date values: {year}-{month}-{day}")
            return None
        
        # Create base datetime
        hour, minute = 0, 0
        
        # Try to parse time if requested
        if include_time:
            time_tuple = parse_bengali_time(bengali_date)
            if time_tuple:
                hour, minute = time_tuple
        
        article_date = datetime(year, month, day, hour, minute)
        
        # Localize to timezone
        localized_date = tz.localize(article_date)
        
        return localized_date
        
    except ValueError as e:
        logger.error(f"Invalid date values in '{bengali_date}': {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error converting Bengali date '{bengali_date}': {e}")
        return None


def convert_bengali_date_to_english_date_only(bengali_date: str) -> Optional[date]:
    """
    Convert Bengali date to English date object (date only, no time).
    For backward compatibility.
    
    Args:
        bengali_date: Bengali date string
        
    Returns:
        Date object or None if conversion fails
    """
    dt = convert_bengali_date_to_english(bengali_date, include_time=False)
    return dt.date() if dt else None


def format_bengali_date(
    dt: Union[datetime, date],
    include_day: bool = False,
    include_time: bool = False
) -> str:
    """
    Format a datetime/date object as a Bengali date string.
    
    Args:
        dt: Datetime or date object
        include_day: Include day name (e.g., শনিবার)
        include_time: Include time (e.g., সকাল ১০:৩০)
        
    Returns:
        Bengali formatted date string
        
    Example:
        >>> format_bengali_date(datetime(2024, 7, 10))
        'জুলাই ১০, ২০২৪'
    """
    # Reverse mappings
    english_to_bengali_months = {v: k for k, v in BENGALI_MONTHS.items() if len(k) > 3}
    english_to_bengali_days = {v: k for k, v in BENGALI_DAYS.items() if 'বার' in k}
    
    month_bn = english_to_bengali_months.get(dt.strftime('%B'), dt.strftime('%B'))
    day_num = english_to_bengali_number(str(dt.day))
    year_bn = english_to_bengali_number(str(dt.year))
    
    result = f"{month_bn} {day_num}, {year_bn}"
    
    if include_day:
        day_name = english_to_bengali_days.get(dt.strftime('%A'), dt.strftime('%A'))
        result = f"{day_name}, {result}"
    
    if include_time and isinstance(dt, datetime):
        hour = dt.hour
        minute = dt.minute
        
        # Determine time period
        if 5 <= hour < 12:
            period = 'সকাল'
        elif 12 <= hour < 15:
            period = 'দুপুর'
        elif 15 <= hour < 18:
            period = 'বিকাল'
        elif 18 <= hour < 20:
            period = 'সন্ধ্যা'
        else:
            period = 'রাত'
        
        # Convert to 12-hour format
        display_hour = hour % 12 or 12
        hour_bn = english_to_bengali_number(str(display_hour))
        minute_bn = english_to_bengali_number(f"{minute:02d}")
        
        result += f", {period} {hour_bn}:{minute_bn}"
    
    return result


# =============================================================================
# BengaliDateParser Class (Object-Oriented Interface)
# =============================================================================

class BengaliDateParser:
    """
    Object-oriented interface for Bengali date parsing.
    
    Provides a reusable parser with configurable timezone and options.
    
    Example:
        >>> parser = BengaliDateParser(timezone='Asia/Dhaka')
        >>> parser.parse("জুলাই ১০, ২০২৪")
        datetime.datetime(2024, 7, 10, 0, 0, tzinfo=<DstTzInfo 'Asia/Dhaka'>)
    """
    
    def __init__(
        self,
        timezone: str = 'Asia/Dhaka',
        include_time: bool = True,
        strict: bool = False
    ):
        """
        Initialize the parser.
        
        Args:
            timezone: Target timezone for parsed dates
            include_time: Whether to parse time components
            strict: If True, raise exceptions instead of returning None
        """
        self.timezone = timezone
        self.include_time = include_time
        self.strict = strict
        
        try:
            self.tz = pytz.timezone(timezone)
        except pytz.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone {timezone}, using Asia/Dhaka")
            self.tz = pytz.timezone('Asia/Dhaka')
    
    def parse(self, date_string: str) -> Optional[datetime]:
        """
        Parse a Bengali date string.
        
        Args:
            date_string: Bengali date string to parse
            
        Returns:
            Timezone-aware datetime object or None
            
        Raises:
            ValueError: If strict mode and parsing fails
        """
        result = convert_bengali_date_to_english(
            date_string,
            timezone=self.timezone,
            include_time=self.include_time
        )
        
        if result is None and self.strict:
            raise ValueError(f"Failed to parse Bengali date: {date_string}")
        
        return result
    
    def parse_date(self, date_string: str) -> Optional[date]:
        """Parse and return date only (no time)."""
        result = self.parse(date_string)
        return result.date() if result else None
    
    def format(
        self, 
        dt: Union[datetime, date],
        include_day: bool = False,
        include_time: bool = False
    ) -> str:
        """Format a datetime object as Bengali date string."""
        return format_bengali_date(dt, include_day, include_time)
    
    def validate(self, date_string: str) -> bool:
        """Check if a string appears to be a valid Bengali date."""
        return validate_bengali_date_format(date_string)
    
    def convert_numbers(self, text: str) -> str:
        """Convert Bengali numerals to English in a string."""
        return bengali_to_english_number(text)


# =============================================================================
# Backward Compatibility Aliases
# =============================================================================

# Legacy function name
bengali_to_english = bengali_to_english_numbers


# =============================================================================
# Module Testing
# =============================================================================

if __name__ == "__main__":
    # Test examples
    test_dates = [
        "জুলাই ১০, ২০২৪",
        "১৫ ডিসেম্বর ২০২৪",
        "ডিসেম্বর ২৫, ২০২৪",
        "জানুয়ারি ১, ২০২৫",
        "১০ আগস্ট ২০২৩",
        "সকাল ১০:৩০, জুলাই ১০, ২০২৪",
        "বিকাল ৫:৪৫, ডিসেম্বর ১৫ ২০২৪",
        "আজ",
        "গতকাল",
    ]
    
    print("Bengali Date Converter Tests")
    print("=" * 50)
    
    parser = BengaliDateParser()
    
    for test in test_dates:
        result = parser.parse(test)
        status = "✓" if result else "✗"
        print(f"{status} '{test}' → {result}")
    
    print("\nNumber Conversion Tests")
    print("-" * 30)
    print(f"'১২৩৪৫' → '{bengali_to_english_number('১২৩৪৫')}'")
    print(f"'২০২৪' → '{bengali_to_english_number('২০২৪')}'")
    
    print("\nFormat Test")
    print("-" * 30)
    now = datetime.now()
    print(f"Now formatted: {format_bengali_date(now, include_day=True, include_time=True)}")