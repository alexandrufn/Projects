"""Guardrail tests: python -m unittest test_guardrails -v
They prove the rules the README promises: nothing fetched is executed, saved or fully downloaded if it is a payload,
and VirusTotal is only queried read-only.
"""
import ast
import http.server
import os
import threading
import time
import unittest

import analyzer

HERE = os.path.dirname(os.path.abspath(__file__))
FORBIDDEN_IMPORTS = {"subprocess", "ctypes", "pickle", "marshal", "multiprocessing", "runpy", "importlib", "code", "pty"}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__", "system", "popen", "startfile", "Popen", "run", "spawn", "execv", "execl"}

PAGES = {
    "/page": ("text/html", b"<html><title>hi</title><body>hello</body></html>"),
    "/disguised": ("text/html", b"MZ\x90\x00\x03" + b"A" * 400_000),                 # EXE posing as a web page
    "/setup.exe": ("text/html", b"<html>looks like text but the path is an installer</html>"),
    "/dl": ("application/octet-stream", b"\x00" * 100_000),
    "/zip": ("text/plain", b"PK\x03\x04" + b"B" * 1000),
}


class _H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        ctype, body = PAGES.get(self.path, ("text/plain", b"nope"))
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except OSError:
            pass

    def log_message(self, *a):
        pass


class SourceRules(unittest.TestCase):
    def _tree(self, name):
        with open(os.path.join(HERE, name), encoding="utf-8") as f:
            return ast.parse(f.read())

    def test_no_code_execution_primitives(self):
        for name in ("analyzer.py", "app.py"):
            for node in ast.walk(self._tree(name)):
                if isinstance(node, ast.Import):
                    bad = {a.name.split(".")[0] for a in node.names} & FORBIDDEN_IMPORTS
                elif isinstance(node, ast.ImportFrom):
                    bad = {(node.module or "").split(".")[0]} & FORBIDDEN_IMPORTS
                elif isinstance(node, ast.Call):
                    fn = node.func  # builtins by name (re.compile etc. are fine); OS-level launchers by attribute
                    if isinstance(fn, ast.Name):
                        bad = {fn.id} & {"eval", "exec", "compile", "__import__"}
                    elif isinstance(fn, ast.Attribute):
                        bad = {fn.attr} & (FORBIDDEN_CALLS - {"eval", "exec", "compile", "__import__"})
                    else:
                        bad = set()
                else:
                    continue
                self.assertFalse(bad, "%s uses forbidden %s (line %d)" % (name, bad, node.lineno))

    def test_only_feed_update_writes_files(self):
        """The only code allowed to write to disk is Feeds.update (blocklist text) and the user-chosen CSV export."""
        allowed = {"analyzer.py": {"update"}, "app.py": {"export"}}
        for name in ("analyzer.py", "app.py"):
            for fn in [n for n in ast.walk(self._tree(name)) if isinstance(n, ast.FunctionDef)]:
                for call in [c for c in ast.walk(fn) if isinstance(c, ast.Call)]:
                    if isinstance(call.func, ast.Name) and call.func.id == "open":
                        mode = ""
                        if len(call.args) > 1 and isinstance(call.args[1], ast.Constant):
                            mode = str(call.args[1].value)
                        for kw in call.keywords:
                            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                                mode = str(kw.value.value)
                        if any(c in mode for c in "wax+"):
                            self.assertIn(fn.name, allowed[name], "%s.%s writes a file" % (name, fn.name))

    def test_virustotal_requests_are_read_only(self):
        with open(os.path.join(HERE, "analyzer.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("/urls\"", src)            # the scan-submission endpoint (POST /urls) is never used
        self.assertIn('urllib.request.Request(VT_BASE + path, headers=', src)  # no data= argument -> always GET


class FetchGuardrails(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _H)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def hop(self, path):
        return analyzer._fetch_hop("http://127.0.0.1:%d%s" % (self.port, path), "127.0.0.1", 5, False)

    def test_normal_page_is_read(self):
        info = self.hop("/page")
        self.assertIn("hello", info["body"])

    def test_disguised_executable_is_dropped(self):
        info = self.hop("/disguised")
        self.assertEqual(info["body"], "")
        self.assertEqual(info["disguised"], "Windows executable")

    def test_file_path_is_never_read_even_if_labelled_html(self):
        info = self.hop("/setup.exe")
        self.assertEqual(info["body"], "")
        self.assertTrue(info["unread"])

    def test_octet_stream_is_never_read(self):
        info = self.hop("/dl")
        self.assertEqual(info["body"], "")
        self.assertTrue(info["download"])

    def test_zip_labelled_text_is_dropped(self):
        self.assertEqual(self.hop("/zip")["body"], "")

    def test_end_to_end_verdicts(self):
        o = {"rdap": False, "allow_private": True}
        r = analyzer.analyze("http://127.0.0.1:%d/disguised" % self.port, o)
        self.assertTrue(any("disguised" in s[2] for s in r["signals"]))
        r = analyzer.analyze("http://127.0.0.1:%d/page" % self.port, {"rdap": False})  # default: private hosts blocked
        self.assertTrue(any("not fetched" in s[2] for s in r["signals"]))


class VirusTotalLogic(unittest.TestCase):
    def setUp(self):
        self._orig = analyzer.vt_get

    def tearDown(self):
        analyzer.vt_get = self._orig

    def test_malicious_url_scores_high_and_exposes_payload_hash(self):
        sha = "a" * 64
        calls = []

        def fake(path, key, timeout=20, stop=None):
            calls.append(path)
            if path.startswith("urls/"):
                return 200, {"data": {"attributes": {"last_analysis_stats": {"malicious": 30, "harmless": 40, "undetected": 10},
                                                     "last_http_response_content_sha256": sha, "threat_names": ["Trojan.X"]}}}
            return 200, {"data": {"attributes": {"last_analysis_stats": {"malicious": 50, "undetected": 10},
                                                 "popular_threat_classification": {"suggested_threat_label": "trojan.agent"}}}}
        analyzer.vt_get = fake
        out = analyzer.vt_lookup_url("http://x.example/a", "KEY")
        self.assertEqual(out["sha256"], sha)
        self.assertEqual(calls[0], "urls/" + analyzer.vt_url_id("http://x.example/a"))
        self.assertEqual(calls[1], "files/" + sha)
        res = analyzer.rescore({"signals": []}, out["signals"])
        self.assertEqual(res["verdict"], "malware")
        self.assertTrue(any("trojan.agent" in s[2] for s in res["signals"]))

    def test_unknown_url_is_not_submitted(self):
        analyzer.vt_get = lambda *a, **k: (404, None)
        out = analyzer.vt_lookup_url("http://x.example/", "KEY")
        self.assertEqual(out["signals"], [])
        self.assertIn("not submitted", out["note"])

    def test_phishing_label_picks_phishing_category(self):
        analyzer.vt_get = lambda *a, **k: (200, {"data": {"attributes": {
            "last_analysis_stats": {"malicious": 12, "harmless": 50}, "threat_names": ["Phishing"]}}})
        out = analyzer.vt_lookup_url("http://x.example/", "KEY")
        self.assertEqual(analyzer.rescore({"signals": []}, out["signals"])["verdict"], "phishing")

    def test_hash_detection_and_links(self):
        for h in ("d41d8cd98f00b204e9800998ecf8427e", "a" * 40, "B" * 64):
            self.assertTrue(analyzer.HASH_RE.match(h))
        self.assertFalse(analyzer.HASH_RE.match("g" * 64))
        self.assertTrue(analyzer.vt_gui_url("a" * 64).endswith("/file/" + "a" * 64))
        self.assertIn("/gui/url/", analyzer.vt_gui_url("http://x.example/"))

    def test_rate_limiter_spaces_requests(self):
        lim = analyzer.VTLimiter(per_minute=600)  # 0.1 s apart
        t = time.time()
        for _ in range(4):
            lim.wait()
        self.assertGreaterEqual(time.time() - t, 0.28)


if __name__ == "__main__":
    unittest.main()
