from datetime import date, timedelta

from CoreFisica.models import AsignacionSemanal
from CoreFisica.views.asignacion_semanal_views import _auto_create_asignacion_semanal_for_week


MONTHS_AHEAD = 36


def add_months(d, months):
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    return date(year, month, 1)


start = date.today().replace(day=1)
end_exclusive = add_months(start, MONTHS_AHEAD)

# Clear existing weekly rows in range so the sequence is rebuilt cleanly.
AsignacionSemanal.objects.filter(week_start__gte=start, week_start__lt=end_exclusive).delete()

weeks_processed = 0
current = start
while current < end_exclusive:
    month = current.month
    d = current
    while d.month == month:
        _auto_create_asignacion_semanal_for_week(d)
        weeks_processed += 1
        d += timedelta(days=7)
    current = add_months(current, 1)

print(f"REGENERATED_WEEKS: {weeks_processed}")
