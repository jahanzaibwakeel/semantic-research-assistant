import unittest

from app.core.tracing import configure_tracing, traced_span


class TracingTests(unittest.TestCase):
    def test_tracing_helpers_are_noops_when_disabled(self):
        configure_tracing()
        with traced_span("test.noop", example="value"):
            value = 1 + 1

        self.assertEqual(value, 2)


if __name__ == "__main__":
    unittest.main()
