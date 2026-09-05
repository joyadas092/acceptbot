import pytest
import re

def parse_and_validate_duration(duration_str: str) -> int | None:
    if not duration_str:
        return None
        
    pattern = r'^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?$'
    match = re.match(pattern, duration_str.strip())
    if not match or not any(match.groups()):
        return None
        
    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0)
    minutes = int(match.group(3) or 0)
    
    total_seconds = days * 86400 + hours * 3600 + minutes * 60
    
    if total_seconds < 0 or total_seconds > 7 * 86400: # max 7 days
        return None
        
    return total_seconds

def test_minutes_only():
    assert parse_and_validate_duration('15m') == 900
    
def test_hours_only():
    assert parse_and_validate_duration('2h') == 7200
    
def test_hours_and_minutes():
    assert parse_and_validate_duration('1h30m') == 5400
    
def test_90_minutes():
    assert parse_and_validate_duration('90m') == 5400
    
def test_zero():
    assert parse_and_validate_duration('0m') == 0
    assert parse_and_validate_duration('0h') == 0
    
def test_invalid_format():
    assert parse_and_validate_duration('abc') is None
    assert parse_and_validate_duration('10s') is None
    
def test_exceeds_max():
    assert parse_and_validate_duration('8d') is None
    
def test_empty_string():
    assert parse_and_validate_duration('') is None
    
def test_negative():
    assert parse_and_validate_duration('-5m') is None
    
def test_decimal():
    assert parse_and_validate_duration('1.5h') is None
