import os
import django
from datetime import date
from django.core.exceptions import ValidationError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.validators import validate_run
from core.services import BusinessDayCalculator

def test_run_validator():
    print("Testing RUN Validator...")
    valid_runs = ['12345678-5', '11111111-1', '12.345.678-5'] # Assuming 12345678-5 is valid for test? No, let's use real valid ones or calculate one.
    # 11.111.111-1 is valid.
    # 30.686.957-4 (Random valid?)
    # Let's use 11.111.111-1 which is valid (1*3+1*2... sum=... mod 11... wait. 11111111:
    # 1*2 + 1*3 + 1*4 + 1*5 + 1*6 + 1*7 + 1*2 + 1*3 = 2+3+4+5+6+7+2+3 = 32. 32%11 = 10. 11-10 = 1. DV=1. Correct.
    
    try:
        validate_run('11.111.111-1')
        print("✅ 11.111.111-1 Valid")
    except ValidationError as e:
        print(f"❌ 11.111.111-1 Invalid: {e}")

    try:
        validate_run('11111111-1')
        print("✅ 11111111-1 Valid")
    except ValidationError as e:
        print(f"❌ 11111111-1 Invalid: {e}")

    invalid_runs = ['11.111.111-2', '12345678-K'] # 12345678-K might be invalid.
    # 12345678: 8*2+7*3+6*4+5*5+4*6+3*7+2*2+1*3 = 16+21+24+25+24+21+4+3 = 138. 138%11 = 6. 11-6 = 5. DV should be 5.
    
    try:
        validate_run('12345678-K')
        print("❌ 12345678-K Should be invalid (DV is 5)")
    except ValidationError:
        print("✅ 12345678-K Invalid (Correct)")

def test_business_days():
    print("\nTesting Business Days...")
    # Friday to Monday
    start = date(2024, 11, 29) # Friday
    # Request 1 day -> Should be Friday
    end = BusinessDayCalculator.calculate_end_date(start, 1)
    print(f"1 day from Fri {start}: {end} (Expected {start}) -> {'✅' if end == start else '❌'}")

    # Request 2 days -> Should be Monday (skip Sat, Sun)
    end = BusinessDayCalculator.calculate_end_date(start, 2)
    expected = date(2024, 12, 2) # Monday
    print(f"2 days from Fri {start}: {end} (Expected {expected}) -> {'✅' if end == expected else '❌'}")

    # Request starting on Saturday -> Should start Monday
    start_sat = date(2024, 11, 30) # Saturday
    end = BusinessDayCalculator.calculate_end_date(start_sat, 1)
    expected = date(2024, 12, 2) # Monday
    print(f"1 day from Sat {start_sat}: {end} (Expected {expected}) -> {'✅' if end == expected else '❌'}")

    # Holiday test (Dec 25 2024 is Wed)
    start_xmas_eve = date(2024, 12, 24) # Tuesday
    # 2 days -> Tue, Thu (Skip Wed)
    end = BusinessDayCalculator.calculate_end_date(start_xmas_eve, 2)
    expected = date(2024, 12, 26) # Thursday
    print(f"2 days from Tue {start_xmas_eve} (Xmas): {end} (Expected {expected}) -> {'✅' if end == expected else '❌'}")

if __name__ == '__main__':
    test_run_validator()
    test_business_days()
