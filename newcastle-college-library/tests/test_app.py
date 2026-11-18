import os, tempfile, unittest
from app import app, init_db

class LibrarySmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        app.config["TESTING"] = True
        import app as module
        module.DATABASE = self.tmp.name
        init_db()
        self.client = app.test_client()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_dashboard_and_catalogue(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/books?q=Hobbit&field=title").status_code, 200)

if __name__ == "__main__":
    unittest.main()
