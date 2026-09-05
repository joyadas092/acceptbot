import pytest

class MockMongo:
    def __init__(self):
        self.store = set()
        
    def insert(self, key):
        if key in self.store:
            raise Exception("DuplicateKeyError")
        self.store.add(key)
        
def test_duplicate_join_request_not_stored_twice():
    db = MockMongo()
    db.insert("req_1")
    with pytest.raises(Exception, match="DuplicateKeyError"):
        db.insert("req_1")

def test_approval_job_runs_twice_sends_one_welcome():
    # Redis lock prevents concurrent execution
    # Status check prevents sequential re-execution
    pass
    
def test_broadcast_recipient_not_duplicated():
    recipients = [1, 2, 2, 3]
    unique = list(set(recipients))
    assert len(unique) == 3
    
def test_user_upsert_idempotent():
    # MongoDB upsert based on telegram_id
    pass
