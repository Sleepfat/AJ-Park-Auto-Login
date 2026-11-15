# unit tests (ไม่แตะเครือข่าย) - รัน: python -m unittest discover -s tests -v
unittest = __import__("unittest")
hashlib = __import__("hashlib")
os = __import__("os")
util = __import__("importlib.util", fromlist=["x"])

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "autologin.py")
spec = util.spec_from_file_location("autologin", PATH)
al = util.module_from_spec(spec)
spec.loader.exec_module(al)

HTML = r"""document.sendin.password.value = hexMD5('\356' + document.login.password.value + '\263\313\356\113\025\206\272\273\215\070\217\113\261\323\311\341');"""
CHAP_ID = bytes([0o356])
CHALLENGE = bytes([0o263, 0o313, 0o356, 0o113, 0o25, 0o206, 0o272, 0o273,
                   0o215, 0o70, 0o217, 0o113, 0o261, 0o323, 0o311, 0o341])


class HashTests(unittest.TestCase):
    def test_make_hash_matches_chap_formula(self):
        expected = hashlib.md5(CHAP_ID + b"secret" + CHALLENGE).hexdigest()
        self.assertEqual(al.make_hash(HTML, b"secret"), expected)

    def test_make_hash_returns_none_without_hexmd5(self):
        self.assertIsNone(al.make_hash("<html>no script here</html>", b"x"))

    def test_unescape_octal_and_hex(self):
        self.assertEqual(al.unescape(r"\101\x42C"), b"ABC")


class ClassifyTests(unittest.TestCase):
    def test_cases(self):
        self.assertEqual(al.classify("Invalid username or password"), "bad_password")
        self.assertEqual(al.classify("no more sessions are allowed"), "limit")
        self.assertEqual(al.classify("user x is already logged in"), "already")
        self.assertEqual(al.classify("<html>welcome</html>"), "sent")


class BackoffTests(unittest.TestCase):
    def test_grows_and_is_capped(self):
        self.assertLess(al.backoff(0), al.INTERVAL + 4)
        self.assertLessEqual(al.backoff(50), al.MAX_BACKOFF + 3)
        self.assertGreater(al.backoff(3), al.backoff(0))


class LogoTests(unittest.TestCase):
    def test_logo_rows_aligned(self):
        self.assertEqual(len(al.LOGO), 6)
        self.assertEqual(len({len(r) for r in al.LOGO}), 1)


if __name__ == "__main__":
    unittest.main()
