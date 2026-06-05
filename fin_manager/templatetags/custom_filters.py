from django import template
from datetime import date

register = template.Library()

@register.filter
def timeuntil_days(value):
    """Calculate days until a date"""
    if not value:
        return None
    today = date.today()
    delta = value - today
    return delta.days

@register.filter
def subtract(value, arg):
    """Subtract arg from value"""
    return value - arg

@register.filter
def cut(value, arg):
    """Remove all occurrences of arg from value"""
    return str(value).replace(arg, '')