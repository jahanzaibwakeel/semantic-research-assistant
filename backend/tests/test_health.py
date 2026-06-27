import os
import unittest


@unittest.skipUnless(os.getenv("RUN_INTEGRATION_TESTS") == "1", "integration services not requested")
class HealthIntegrationTests(unittest.TestCase):
    def test_app_imports_with_service_configuration(self):
        from app.main import create_app

        app = create_app()
        self.assertEqual(app.title, "Semantic Research Assistant")


if __name__ == "__main__":
    unittest.main()
