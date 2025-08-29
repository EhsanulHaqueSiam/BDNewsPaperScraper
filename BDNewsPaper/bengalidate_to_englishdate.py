import logging
import re
from datetime import datetime, date
from typing import List, Optional, Union

import pytz

# Configure logging
logger = logging.getLogger(__name__)

# Mapping of Bengali months to English months
BENGALI_MONTHS = {
    'জানুয়ারি': 'January',
    'ফেব্রুয়ারি': 'February',
    'মার্চ': 'March',
    'এপ্রিল': 'April',
    'মে': 'May',
    'জুন': 'June',
    'জুলাই': 'July',
    'আগস্ট': 'August',
    'সেপ্টেম্বর': 'September',
    'অক্টোবর': 'October',
    'নভেম্বর': 'November',
    'ডিসেম্বর': 'December'
}

# Bengali to English number mapping (optimized as dictionary for O(1) lookup)
BENGALI_TO_ENGLISH_NUMS = {
    '১': '1', '২': '2', '৩': '3', '৪': '4', '৫': '5',
    '৬': '6', '৭': '7', '৮': '8', '৯': '9', '০': '0'
}


def bengali_to_english_numbers(text_list: List[str]) -> List[str]:
    """
    Convert Bengali numerals to English numerals in a list of strings.
    
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
            
        # Convert Bengali numerals to English using dictionary mapping
        english_text = ''.join(
            BENGALI_TO_ENGLISH_NUMS.get(char, char) for char in text
        )
        converted_nums.append(english_text)
    
    return converted_nums


def validate_bengali_date_format(bengali_date: str) -> bool:
    """
    Validate Bengali date string format.
    
    Args:
        bengali_date: Bengali date string to validate
        
    Returns:
        True if format is valid, False otherwise
    """
    if not isinstance(bengali_date, str):
        return False
    
    # Check if string contains Bengali characters and has expected structure
    # Pattern: Bengali_month Bengali_day, Bengali_year
    pattern = r'^[অ-৯\s]+\s+[০-৯]+,?\s+[০-৯]+$'
    return bool(re.match(pattern, bengali_date.strip()))


def parse_bengali_date_components(bengali_date: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse Bengali date string into components.
    
    Args:
        bengali_date: Bengali date string
        
    Returns:
        Tuple of (month, day, year) or (None, None, None) if parsing fails
    """
    try:
        # Clean and split the date string
        cleaned_date = bengali_date.strip()
        
        # Handle different possible formats
        # Format 1: "মাস দিন, বছর" (Month Day, Year)
        if ',' in cleaned_date:
            parts = cleaned_date.split(',')
            if len(parts) == 2:
                month_day_part = parts[0].strip().split()
                year_part = parts[1].strip()
                
                if len(month_day_part) >= 2:
                    month = month_day_part[0]
                    day = month_day_part[1]
                    year = year_part
                    return month, day, year
        
        # Format 2: "মাস দিন বছর" (Month Day Year)
        parts = cleaned_date.split()
        if len(parts) >= 3:
            month = parts[0]
            day = parts[1]
            year = parts[2]
            return month, day, year
            
        return None, None, None
        
    except Exception as e:
        logger.error(f"Error parsing Bengali date components: {e}")
        return None, None, None


def convert_bengali_date_to_english(bengali_date: str, timezone: str = 'Asia/Dhaka') -> Optional[datetime]:
    """
    Convert Bengali date string to timezone-aware English datetime object.
    
    Args:
        bengali_date: Bengali date string (e.g., "জুলাই ১০, ২০২৪")
        timezone: Target timezone (default: 'Asia/Dhaka')
        
    Returns:
        Timezone-aware datetime object or None if conversion fails
        
    Example:
        >>> convert_bengali_date_to_english("জুলাই ১০, ২০২৪")
        datetime.datetime(2024, 7, 10, 0, 0, tzinfo=<DstTzInfo 'Asia/Dhaka' +06+6:00:00 STD>)
    """
    if not bengali_date or not isinstance(bengali_date, str):
        logger.error("Invalid input: Bengali date must be a non-empty string")
        return None
    
    # Validate input format
    if not validate_bengali_date_format(bengali_date):
        logger.error(f"Invalid Bengali date format: {bengali_date}")
        return None
    
    try:
        # Parse date components
        month_bengali, day_bengali, year_bengali = parse_bengali_date_components(bengali_date)
        
        if not all([month_bengali, day_bengali, year_bengali]):
            logger.error(f"Failed to parse Bengali date components from: {bengali_date}")
            return None
        
        # Convert Bengali month to English
        month_english = BENGALI_MONTHS.get(month_bengali.strip() if month_bengali else "")
        if not month_english:
            logger.error(f"Unknown Bengali month: {month_bengali}")
            return None
        
        # Convert Bengali numerals to English
        try:
            day_english = bengali_to_english_numbers([day_bengali.strip() if day_bengali else ""])[0]
            year_english = bengali_to_english_numbers([year_bengali.strip() if year_bengali else ""])[0]
        except (ValueError, TypeError) as e:
            logger.error(f"Error converting Bengali numerals: {e}")
            return None
        
        # Validate converted numbers
        if not day_english.isdigit() or not year_english.isdigit():
            logger.error(f"Invalid numeric conversion: day={day_english}, year={year_english}")
            return None
        
        # Create English date string and parse
        english_date_str = f"{month_english} {day_english}, {year_english}"
        
        try:
            # Parse the date
            article_date = datetime.strptime(english_date_str, "%B %d, %Y")
            
            # Convert to timezone-aware datetime
            tz = pytz.timezone(timezone)
            localized_date = tz.localize(article_date)
            
            return localized_date
            
        except ValueError as e:
            logger.error(f"Invalid date values in '{english_date_str}': {e}")
            return None
            
    except Exception as e:
        logger.error(f"Unexpected error converting Bengali date '{bengali_date}': {e}")
        return None


def convert_bengali_date_to_english_date_only(bengali_date: str) -> Optional[date]:
    """
    Convert Bengali date to English date object (for backward compatibility).
    
    Args:
        bengali_date: Bengali date string
        
    Returns:
        Date object or None if conversion fails
    """
    dt = convert_bengali_date_to_english(bengali_date)
    return dt.date() if dt else None


# Backward compatibility aliases
bengali_to_english = bengali_to_english_numbers