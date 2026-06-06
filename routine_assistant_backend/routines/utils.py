from calendar import monthrange
from datetime import date, timedelta


def _add_month(current_date: date, target_day: int) -> date:
    month = current_date.month + 1
    year = current_date.year

    if month > 12:
        month = 1
        year += 1

    last_day = monthrange(year, month)[1]
    return date(year, month, min(target_day, last_day))


def generate_dates(start_date: date, end_date: date, frequency: str) -> list[date]:
    if frequency == "once":
        return [start_date]

    dates: list[date] = []
    current_date = start_date

    while current_date <= end_date:
        dates.append(current_date)

        if frequency == "daily":
            current_date += timedelta(days=1)
        elif frequency == "weekly":
            current_date += timedelta(days=7)
        elif frequency == "monthly":
            current_date = _add_month(current_date, start_date.day)
        else:
            break

    return dates
