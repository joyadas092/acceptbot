import pytest

def is_super_admin(user_id, admin_list):
    return user_id in admin_list
    
def is_callback_owner(callback_user_id, owner_id):
    return callback_user_id == owner_id

def test_super_admin_filter_allows_super_admin():
    admin_list = [123, 456]
    assert is_super_admin(123, admin_list) is True
    
def test_super_admin_filter_blocks_normal_user():
    admin_list = [123, 456]
    assert is_super_admin(789, admin_list) is False
    
def test_callback_owner_allows_owner():
    assert is_callback_owner(123, 123) is True
    
def test_callback_owner_blocks_non_owner():
    assert is_callback_owner(123, 456) is False
    
# Throttling logic would be tested with mock redis
def test_throttling_allows_within_limit():
    pass
    
def test_throttling_blocks_over_limit():
    pass
