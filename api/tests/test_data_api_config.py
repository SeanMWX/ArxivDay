import importlib
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_NAME = "api.data_api"


class DataApiConfigTests(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop(MODULE_NAME, None)

    def import_data_api(self):
        sys.modules.pop(MODULE_NAME, None)
        return importlib.import_module(MODULE_NAME)

    def test_imports_and_reads_configuration_from_env_without_config_file(self):
        env = {
            "DB_HOST": "db.example.com",
            "DB_PORT": "3307",
            "DB_USER": "arxiv_user",
            "DB_PASSWORD": "secret",
            "DB_NAME": "arxiv_prod",
            "API_KEY": "api-secret",
            "ARXIV_TABLE": "env_articles",
            "CATEGORIES": "cs.AI, cs.LG",
            "API_PORT": "8100",
            "SYNC_DB_PATH": "/data/sync.db",
        }

        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(os.environ, env, clear=False):
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                module = self.import_data_api()
                db_config = module.config.db_config()
                categories = module.config.categories()
                api_key = module.config.api_key()
                port = module.config.server_port()
                sync_db_path = module.SYNC_DB_PATH
                app_table = module.app.state.table
            finally:
                os.chdir(old_cwd)

        self.assertEqual(db_config["host"], "db.example.com")
        self.assertEqual(db_config["port"], 3307)
        self.assertEqual(db_config["user"], "arxiv_user")
        self.assertEqual(db_config["password"], "secret")
        self.assertEqual(db_config["db"], "arxiv_prod")
        self.assertEqual(categories, ["cs.AI", "cs.LG"])
        self.assertEqual(api_key, "api-secret")
        self.assertEqual(port, 8100)
        self.assertEqual(sync_db_path, "/data/sync.db")
        self.assertEqual(app_table, "env_articles")

    def test_config_file_fallback_still_works(self):
        config_text = textwrap.dedent(
            """
            [database]
            host=localhost
            port=3308
            user=file_user
            password=file_secret
            database=arxiv_file

            [settings]
            arxiv_table=file_articles
            categories=cs.CR, cs.CL

            [api]
            key=file-api-secret

            [server]
            port=8200
            """
        )

        env_keys = [
            "DB_HOST",
            "DB_PORT",
            "DB_USER",
            "DB_PASSWORD",
            "DB_NAME",
            "API_KEY",
            "ARXIV_TABLE",
            "CATEGORIES",
            "API_PORT",
            "PORT",
        ]

        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(os.environ, {}, clear=False):
            for key in env_keys:
                os.environ.pop(key, None)
            config_path = Path(tmpdir) / "config.ini"
            config_path.write_text(config_text, encoding="utf-8")

            module = self.import_data_api()
            cfg = module.Config(str(config_path))
            db_config = cfg.db_config()
            articles_table = cfg.articles_table()
            categories = cfg.categories()
            api_key = cfg.api_key()
            port = cfg.server_port()

        self.assertEqual(db_config["host"], "localhost")
        self.assertEqual(db_config["port"], 3308)
        self.assertEqual(db_config["user"], "file_user")
        self.assertEqual(db_config["password"], "file_secret")
        self.assertEqual(db_config["db"], "arxiv_file")
        self.assertEqual(articles_table, "file_articles")
        self.assertEqual(categories, ["cs.CR", "cs.CL"])
        self.assertEqual(api_key, "file-api-secret")
        self.assertEqual(port, 8200)


if __name__ == "__main__":
    unittest.main()
