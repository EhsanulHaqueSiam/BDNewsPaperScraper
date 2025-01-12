from datetime import datetime
import time

# Mapping of Bengali months to English months
bengali_months = {
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

def bengali_to_english(numList):
    bengaliNums = ["১", "২", "৩", "৪", "৫", "৬", "৭", "৮", "৯", "০"]
    engNums = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
    convertedNums = []
    for j in numList:
        englishNum = ''
        for a in j:
            if a in bengaliNums:
                i = bengaliNums.index(a)
                englishNum += engNums[i]
        convertedNums.append(englishNum)
    return convertedNums

def convert_bengali_date_to_english(bengali_date):
    try:
        # Split the date string into month, day, and year
        month_bengali, day_bengali, year_bengali = bengali_date.split(' ')
        day_bengali = day_bengali.strip(',')

        # Convert Bengali month to English
        month_english = bengali_months.get(month_bengali.strip(), None)
        day_english = bengali_to_english([day_bengali.strip()])[0]
        year_english = bengali_to_english([year_bengali.strip()])[0]

        if month_english:
            # Create the English date string
            english_date_str = f"{month_english} {day_english}, {year_english}"
            # Convert to datetime object
            article_date = datetime.strptime(english_date_str, "%B %d, %Y")
            return article_date.date()
        else:
            raise ValueError("Invalid Bengali month")
    except Exception as e:
        print(f"Error: {e}")
        return None
