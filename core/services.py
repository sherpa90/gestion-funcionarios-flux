from datetime import timedelta, date

class BusinessDayCalculator:
    # Feriados hardcoded para 2024-2025 (Ejemplo simplificado)
    # En producción esto debería venir de una BD o API
    HOLIDAYS = [
        date(2024, 1, 1), date(2024, 3, 29), date(2024, 3, 30),
        date(2024, 5, 1), date(2024, 5, 21), date(2024, 6, 20),
        date(2024, 7, 16), date(2024, 8, 15), date(2024, 9, 18),
        date(2024, 9, 19), date(2024, 9, 20), date(2024, 10, 12),
        date(2024, 10, 31), date(2024, 11, 1), date(2024, 12, 8),
        date(2024, 12, 25),
        date(2025, 1, 1),
    ]

    @classmethod
    def is_business_day(cls, day):
        # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
        if day.weekday() >= 5:
            return False
        if day in cls.HOLIDAYS:
            return False
        return True

    @classmethod
    def calculate_end_date(cls, start_date, duration_days):
        """
        Calcula la fecha de término dado una fecha de inicio y duración en días hábiles.
        Si duration_days es 0.5, se considera el mismo día.
        """
        if duration_days <= 0.5:
            return start_date
            
        current_date = start_date
        days_added = 0
        
        # Si el día de inicio no es hábil, avanzamos al siguiente hábil
        while not cls.is_business_day(current_date):
            current_date += timedelta(days=1)
            
        # Consumimos el primer día
        days_added = 1 # El día de inicio cuenta como 1 día consumido si es entero
        
        # Si duration es 1, retornamos el mismo día (si es hábil)
        if duration_days == 1:
            return current_date

        # Para duraciones > 1
        remaining_days = duration_days - 1
        
        while remaining_days > 0:
            current_date += timedelta(days=1)
            if cls.is_business_day(current_date):
                remaining_days -= 1
                
        return current_date

    @classmethod
    def count_business_days(cls, start_date, end_date):
        """
        Cuenta los días hábiles entre dos fechas (inclusive).
        """
        count = 0
        current = start_date
        while current <= end_date:
            if cls.is_business_day(current):
                count += 1
            current += timedelta(days=1)
        return count
