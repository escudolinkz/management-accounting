from app import repo

class DummyRule:
    def __init__(self, pattern, priority, id, category_id=None, subcategory=None, status='active'):
        self.pattern = pattern
        self.priority = priority
        self.id = id
        self.category_id = category_id
        self.subcategory = subcategory
        self.status = status

class DummyTransaction:
    def __init__(self, description):
        self.description = description
        self.category_id = None
        self.subcategory = None


def test_apply_rules_orders_by_priority_then_id():
    tx = DummyTransaction('Coffee shop')
    rules = [
        DummyRule('coffee', priority=2, id=2, category_id=1),
        DummyRule('coffee', priority=1, id=3, category_id=2),
        DummyRule('coffee', priority=1, id=1, category_id=3),
    ]
    repo.apply_rules(None, tx, rules)
    # Rule with priority 1 and lowest id (1) should be applied
    assert tx.category_id == 3
    assert tx.subcategory is None
