import re
from datetime import timedelta


TIME_RE = re.compile(r"(\d+)\s*(d|dia|dias|h|hr|hrs|hora|horas|m|min|mins|minuto|minutos)", re.I)


def parse_duration(text: str) -> timedelta:
    text = (text or "").strip().lower()
    total = timedelta()

    for amount_text, unit in TIME_RE.findall(text):
        amount = int(amount_text)
        unit = unit.lower()

        if unit in {"d", "dia", "dias"}:
            total += timedelta(days=amount)
        elif unit in {"h", "hr", "hrs", "hora", "horas"}:
            total += timedelta(hours=amount)
        elif unit in {"m", "min", "mins", "minuto", "minutos"}:
            total += timedelta(minutes=amount)

    if total.total_seconds() <= 0:
        raise ValueError("Duracion invalida. Usa algo como `30m`, `2h`, `1d` o `1h30m`.")

    return total

