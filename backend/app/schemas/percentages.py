def normalize_percent_style(value: object) -> object:
    if value is None:
        return value
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    if number > 1:
        return number / 100
    return value
