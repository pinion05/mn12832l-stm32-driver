import unittest

from mn12832l.menu.app import MenuApp


class MenuAppImportTests(unittest.TestCase):
    """헤드리스 CI에서도 import와 클래스 구조가 깨지지 않는지 확인."""

    def test_app_class_exists_with_expected_interface(self) -> None:
        self.assertTrue(hasattr(MenuApp, "setup"))
        self.assertTrue(hasattr(MenuApp, "tick"))
        self.assertTrue(hasattr(MenuApp, "start"))
        self.assertTrue(hasattr(MenuApp, "on_close"))

    def test_app_requires_engine_arg(self) -> None:
        import inspect
        sig = inspect.signature(MenuApp.__init__)
        self.assertIn("engine", sig.parameters)


if __name__ == "__main__":
    unittest.main()
