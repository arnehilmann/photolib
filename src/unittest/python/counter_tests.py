import unittest

from photolib.transfer import Counter


class CounterTest(unittest.TestCase):

    def test_init(self):
        counter = Counter()
        self.assertEqual(counter.get(), {})

    def test_inc(self):
        counter = Counter()
        counter.inc("foo")
        self.assertEqual(counter.get(), {"foo": 1})

    def test_reset(self):
        counter = Counter()
        counter.inc("foo")
        counter.reset()
        self.assertEqual(counter.get(), {})

if __name__ == "__main__":
    unittest.main()
