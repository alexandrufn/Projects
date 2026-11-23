"""URL analysis engine: URL structure, reputation feeds, DNS/TLS, domain age and page content
are turned into weighted signals, then summed into a verdict (clean / suspicious / phishing / malware).

Safety: pages are only downloaded as text (capped size), never executed, never saved; binary
downloads are detected from headers and not read; hosts resolving to private addresses are not fetched.
"""
import base64
import datetime
import hashlib
import http.client
import ipaddress
import json
import math
import os
import re
import socket
import ssl
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
FEED_DIR = os.path.join(HERE, "data", "feeds")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
MAX_BODY = 400_000
MAX_REDIRECTS = 6

# brand -> domains that legitimately belong to it
BRANDS = {
    "paypal": {"paypal.com"}, "microsoft": {"microsoft.com", "live.com", "office.com", "microsoftonline.com", "outlook.com"},
    "office365": {"office.com", "microsoft.com"}, "outlook": {"outlook.com", "live.com", "office.com"},
    "google": {"google.com", "gmail.com", "youtube.com", "gstatic.com"}, "gmail": {"google.com", "gmail.com"},
    "apple": {"apple.com", "icloud.com"}, "icloud": {"icloud.com", "apple.com"},
    "amazon": {"amazon.com", "amazon.de", "amazon.co.uk", "amazonaws.com", "amazon.fr", "amazon.it", "amazon.es"},
    "facebook": {"facebook.com", "fb.com", "meta.com"}, "instagram": {"instagram.com"},
    "whatsapp": {"whatsapp.com", "whatsapp.net"}, "telegram": {"telegram.org", "t.me"},
    "netflix": {"netflix.com"}, "linkedin": {"linkedin.com"}, "twitter": {"twitter.com", "x.com"},
    "dropbox": {"dropbox.com"}, "docusign": {"docusign.com", "docusign.net"}, "adobe": {"adobe.com"},
    "steam": {"steampowered.com", "steamcommunity.com"}, "binance": {"binance.com"}, "coinbase": {"coinbase.com"},
    "metamask": {"metamask.io"}, "chase": {"chase.com"}, "wellsfargo": {"wellsfargo.com"},
    "bankofamerica": {"bankofamerica.com"}, "citibank": {"citi.com", "citibank.com"},
    "dhl": {"dhl.com", "dhl.de"}, "fedex": {"fedex.com"}, "ups": {"ups.com"}, "usps": {"usps.com"},
    "fancourier": {"fancourier.ro"}, "sameday": {"sameday.ro"}, "emag": {"emag.ro", "emag.hu", "emag.bg"},
    "bancatransilvania": {"bancatransilvania.ro", "bt24.ro"}, "raiffeisen": {"raiffeisen.ro", "raiffeisen.at"},
    "ing": {"ing.ro", "ing.com", "ing.nl", "ing.de"}, "brd": {"brd.ro"}, "cec": {"cec.ro"},
    "anaf": {"anaf.ro"}, "posta-romana": {"posta-romana.ro"}, "orange": {"orange.ro", "orange.com", "orange.fr"},
    "vodafone": {"vodafone.ro", "vodafone.com"}, "revolut": {"revolut.com"}, "norton": {"norton.com", "nortonlifelock.com"},
    "mcafee": {"mcafee.com"}, "avast": {"avast.com"}, "avg": {"avg.com"}, "gendigital": {"gendigital.com"},
}
TRUSTED = set().union(*BRANDS.values()) | {
    "wikipedia.org", "github.com", "stackoverflow.com", "mozilla.org", "cloudflare.com", "bing.com", "yahoo.com",
    "reddit.com", "ebay.com", "zoom.us", "slack.com", "atlassian.com", "python.org", "openai.com", "anthropic.com",
    "claude.ai", "wordpress.com", "medium.com", "nytimes.com", "bbc.com", "bbc.co.uk",
}
# hosting platforms where many unrelated (good and bad) sites live: never trust or condemn by host alone
SHARED_HOSTING = {
    "github.io", "githubusercontent.com", "googleapis.com", "amazonaws.com", "blogspot.com", "firebaseapp.com",
    "web.app", "pages.dev", "workers.dev", "herokuapp.com", "vercel.app", "netlify.app", "dropbox.com",
    "googleusercontent.com", "weebly.com", "wixsite.com", "000webhostapp.com", "azurewebsites.net",
    "cloudfront.net", "ipfs.io", "r2.dev", "sharepoint.com", "onrender.com", "glitch.me", "repl.co",
}
MULTI_SUFFIX = {
    "co.uk", "org.uk", "ac.uk", "com.au", "net.au", "com.br", "co.jp", "co.in", "co.za", "com.tr", "com.ro",
    "com.mx", "com.ar", "co.nz", "com.cn", "com.hk", "com.sg", "com.ua", "com.pl",
}
SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly", "rebrand.ly", "ow.ly", "shorturl.at",
    "tiny.cc", "buff.ly", "rb.gy", "t.ly", "s.id", "lnkd.in", "v.gd", "qrco.de",
}
RISKY_TLDS = {
    "zip", "mov", "top", "xyz", "click", "link", "gq", "tk", "ml", "cf", "ga", "icu", "buzz", "cyou", "cfd",
    "sbs", "monster", "rest", "support", "country", "men", "loan", "work", "bid", "date", "download", "stream",
}
EXEC_EXT = {"exe", "msi", "scr", "bat", "cmd", "ps1", "vbs", "vbe", "js", "jse", "jar", "apk", "dmg", "iso",
            "img", "lnk", "hta", "docm", "xlsm", "pptm", "pif", "com", "wsf", "dll", "cpl"}
ARCHIVE_EXT = {"zip", "rar", "7z", "gz", "tar", "cab", "arj"}
KEYWORDS = ("login", "signin", "sign-in", "verify", "verification", "secure", "account", "update", "confirm",
            "banking", "password", "wallet", "invoice", "payment", "suspend", "unlock", "recover", "billing",
            "authenticate", "validate", "security-alert")
DOWNLOAD_TYPES = ("application/octet-stream", "application/x-msdownload", "application/x-msdos-program",
                  "application/zip", "application/x-zip", "application/x-rar", "application/x-7z",
                  "application/java-archive", "application/vnd.android.package-archive",
                  "application/x-dosexec", "application/x-msi", "application/x-sh", "application/hta")

_LEET = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "$": "s", "!": "i"})


# --------------------------------------------------------------------------- helpers
def normalize(raw):
    """Clean user input (including defanged hxxp / [.] forms). Returns (url, scheme_was_guessed)."""
    s = raw.strip().strip("<>\"'")
    if not s or s.startswith("#"):
        return None, False
    s = re.sub(r"^hxxp", "http", s, flags=re.I).replace("[.]", ".").replace("(.)", ".").replace("[:]", ":")
    guessed = "://" not in s
    if guessed:
        s = "https://" + s
    try:
        parts = urlsplit(s)
        host = parts.hostname
    except ValueError:
        return None, False
    if parts.scheme.lower() not in ("http", "https") or not host or re.search(r"[\s/\\]", host) \
            or not re.fullmatch(r"[^\W_][\w.-]*|[0-9a-f:.]+", host, re.I):
        return None, False
    if "." not in host and ":" not in host and not host.replace(".", "").isdigit():
        return None, False
    return s, guessed


def split_host(host):
    """-> (subdomain, registrable domain)"""
    labels = host.lower().strip(".").split(".")
    if len(labels) <= 2:
        return "", ".".join(labels)
    if ".".join(labels[-2:]) in MULTI_SUFFIX and len(labels) >= 3:
        return ".".join(labels[:-3]), ".".join(labels[-3:])
    return ".".join(labels[:-2]), ".".join(labels[-2:])


def entropy(s):
    if not s:
        return 0.0
    return -sum(c / len(s) * math.log2(c / len(s)) for c in (s.count(ch) for ch in set(s)))


def edit_distance(a, b):
    if abs(len(a) - len(b)) > 2:
        return 9
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def is_private(ips):
    for ip in ips:
        try:
            if not ipaddress.ip_address(ip.split("%")[0]).is_global:
                return True
        except ValueError:
            return True
    return False


def resolve(host):
    infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return sorted({i[4][0] for i in infos}, key=lambda ip: ":" in ip)  # IPv4 first


def defang(url):
    return re.sub(r"^http", "hxxp", url, flags=re.I).replace(".", "[.]")


# --------------------------------------------------------------------------- reputation feeds
class Feeds:
    SOURCES = (("openphish.txt", "https://openphish.com/feed.txt", "phishing"),
               ("urlhaus.txt", "https://urlhaus.abuse.ch/downloads/text_online/", "malware"))

    def __init__(self):
        self.urls, self.hosts, self.counts = {}, {}, {}

    @staticmethod
    def _key(url):
        return re.sub(r"^https?://", "", url.strip().lower()).rstrip("/")

    def load(self):
        self.urls, self.hosts, self.counts = {}, {}, {}
        for fname, _, cat in self.SOURCES:
            path = os.path.join(FEED_DIR, fname)
            if not os.path.exists(path):
                continue
            n = 0
            with open(path, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    self.urls[self._key(line)] = cat
                    try:
                        h = (urlsplit(line).hostname or "").lower()
                    except ValueError:
                        continue
                    if h:
                        self.hosts.setdefault(h, cat)
                    n += 1
            self.counts[cat] = n
        return self.counts

    def update(self):
        """Download feeds; returns a list of status lines."""
        os.makedirs(FEED_DIR, exist_ok=True)
        out = []
        for fname, url, cat in self.SOURCES:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "UrlClassifier/1.0"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = r.read(30_000_000)
                tmp = os.path.join(FEED_DIR, fname + ".tmp")
                with open(tmp, "wb") as f:
                    f.write(data)
                os.replace(tmp, os.path.join(FEED_DIR, fname))
                out.append("%s: OK" % fname)
            except Exception as e:  # noqa: BLE001 - report any failure to the user
                out.append("%s: failed (%s)" % (fname, str(e)[:80]))
        self.load()
        return out

    def match(self, url, host, reg):
        sig = []
        cat = self.urls.get(self._key(url))
        if cat:
            sig.append((cat, 90, "URL is listed in a known-%s feed" % cat))
        elif reg not in SHARED_HOSTING and reg not in TRUSTED:
            hcat = self.hosts.get(host)
            if hcat:
                sig.append((hcat, 40, "host serves other URLs listed in a known-%s feed" % hcat))
        return sig


FEEDS = Feeds()
FEEDS.load()


# --------------------------------------------------------------------------- domain age (RDAP)
_rdap_cache, _rdap_lock, _rdap_sem = {}, threading.Lock(), threading.Semaphore(4)


def domain_age_days(reg, timeout=8):
    with _rdap_lock:
        if reg in _rdap_cache:
            return _rdap_cache[reg]
    age = None
    try:
        ascii_reg = reg.encode("idna").decode("ascii")
        with _rdap_sem:
            req = urllib.request.Request("https://rdap.org/domain/" + ascii_reg,
                                         headers={"Accept": "application/rdap+json", "User-Agent": "UrlClassifier/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.load(r)
        for ev in data.get("events", []):
            if ev.get("eventAction") == "registration":
                dt = datetime.datetime.fromisoformat(ev["eventDate"].replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                age = (datetime.datetime.now(datetime.timezone.utc) - dt).days
                break
    except Exception:  # noqa: BLE001 - lookup is best effort
        pass
    with _rdap_lock:
        _rdap_cache[reg] = age
    return age


# --------------------------------------------------------------------------- lexical checks
def lexical(url, add, prefix=""):
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        add("generic", 15, prefix + "malformed URL")
        return
    sub, reg = split_host(host)
    tld = host.rsplit(".", 1)[-1]
    path_q = (parts.path + "?" + parts.query).lower()
    label = reg.split(".")[0]

    is_ip = False
    try:
        ipaddress.ip_address(host)
        is_ip = True
        add("generic", 25, prefix + "uses a raw IP address instead of a domain name")
    except ValueError:
        if re.fullmatch(r"\d{6,10}|0x[0-9a-f]+", host):
            is_ip = True
            add("generic", 30, prefix + "obfuscated numeric IP address")
    if parts.username is not None:
        if "." in parts.username:
            add("phishing", 50, prefix + "'%s@' prefix makes the URL look like another site" % parts.username[:40])
        else:
            add("phishing", 25, prefix + "'user@' in URL can disguise the real host")
    if len(url) > 200:
        add("generic", 10, prefix + "very long URL (%d chars)" % len(url))
    elif len(url) > 100:
        add("generic", 5, prefix + "long URL (%d chars)" % len(url))
    if not is_ip:
        n_sub = len(sub.split(".")) if sub else 0
        if n_sub >= 4:
            add("generic", 10, prefix + "%d nested subdomains" % n_sub)
        elif n_sub == 3:
            add("generic", 5, prefix + "3 nested subdomains")
        if label.count("-") >= 2:
            add("generic", 8, prefix + "several hyphens in domain name")
        if len(label) > 6 and sum(c.isdigit() for c in label) / len(label) > 0.3:
            add("generic", 6, prefix + "many digits in domain name")
        if len(label) >= 12 and entropy(label) > 3.6:
            add("malware", 12, prefix + "random-looking domain name (possible generated domain)")
        if "xn--" in host:
            add("phishing", 30, prefix + "punycode / internationalised domain (possible homograph)")
        if tld in RISKY_TLDS:
            add("generic", 10, prefix + "high-abuse TLD .%s" % tld)
        if reg in SHORTENERS:
            add("generic", 8, prefix + "link shortener hides the real destination")
    if port not in (None, 80, 443):
        add("generic", 8, prefix + "non-standard port %s" % port)
    if parts.scheme == "http" and any(k in host + path_q for k in ("login", "signin", "verify", "password", "account")):
        add("phishing", 8, prefix + "login-style keywords over plain HTTP")
    if url.count("%") > 5:
        add("generic", 5, prefix + "heavily percent-encoded URL")
    if re.search(r"https?(://|%3a%2f%2f)", path_q):
        add("generic", 6, prefix + "another URL embedded in path/query (redirect-style)")

    kw = [k for k in KEYWORDS if k in host + path_q]
    if len(kw) >= 2:
        add("phishing", 10, prefix + "sensitive keywords: " + ", ".join(kw[:4]))
    elif kw:
        add("phishing", 4, prefix + "keyword '%s' in URL" % kw[0])

    ext = parts.path.rsplit(".", 1)[-1].lower() if "." in parts.path.rsplit("/", 1)[-1] else ""
    if ext in EXEC_EXT:
        add("malware", 25, prefix + "URL points to an executable/script file (.%s)" % ext)
    elif ext in ARCHIVE_EXT:
        add("malware", 10, prefix + "URL points to an archive (.%s)" % ext)

    # brand impersonation
    if not is_ip and reg not in TRUSTED:
        tokens = [t for t in re.split(r"[^a-z0-9]+", (sub + "." + label + " " + parts.path).lower()) if t]
        norm_label = label.translate(_LEET).replace("rn", "m").replace("vv", "w").replace("-", "")
        best = None
        for brand, legit in BRANDS.items():
            if reg in legit:
                continue
            b = brand.replace("-", "")
            if norm_label == b or (len(b) >= 5 and edit_distance(norm_label, b) == 1):
                best = (35, "domain '%s' looks like a lookalike of '%s'" % (reg, brand))
                break
            hostnorm = (sub + label).translate(_LEET).replace("-", "")
            in_host = (len(b) >= 5 and b in hostnorm) or brand in re.split(r"[^a-z0-9]+", sub + "." + label)
            in_path = brand in tokens or (len(b) >= 5 and b in parts.path.lower())
            if in_host and (not best or best[0] < 30):
                best = (30, "brand '%s' used in domain, but site is not theirs" % brand)
            elif in_path and (not best or best[0] < 15):
                best = (15, "brand '%s' appears in URL path of an unrelated domain" % brand)
        if best:
            add("phishing", best[0], prefix + best[1])


# --------------------------------------------------------------------------- network fetch
class _PinnedHTTP(http.client.HTTPConnection):
    def __init__(self, host, port, ip, **kw):
        super().__init__(host, port, **kw)
        self._ip = ip

    def connect(self):
        self.sock = socket.create_connection((self._ip, self.port), self.timeout)


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, port, ip, **kw):
        super().__init__(host, port, **kw)
        self._ip = ip

    def connect(self):
        sock = socket.create_connection((self._ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


MAGIC = ((b"MZ", "Windows executable"), (b"PK\x03\x04", "ZIP/Office/APK archive"), (b"\x7fELF", "Linux executable"),
         (b"%PDF", "PDF"), (b"Rar!", "RAR archive"), (b"7z\xbc\xaf", "7-Zip archive"), (b"\xd0\xcf\x11\xe0", "legacy Office/MSI"),
         (b"\xca\xfe\xba\xbe", "Java class / Mach-O"), (b"\xcf\xfa\xed\xfe", "Mach-O executable"), (b"MSCF", "CAB archive"),
         (b"\x1f\x8b", "gzip archive"), (b"\x89PNG", "image"), (b"GIF8", "image"), (b"\xff\xd8\xff", "image"),
         (b"#!/", "shell script"), (b"\xef\xbb\xbf#!/", "shell script"))


def sniff_binary(head):
    """Identify non-text content from its first bytes (so a disguised payload is dropped after 16 bytes)."""
    for sig, name in MAGIC:
        if head.startswith(sig):
            return name
    return None


def _fetch_hop(url, ip, timeout, verify):
    parts = urlsplit(url)
    https = parts.scheme == "https"
    port = parts.port or (443 if https else 80)
    if https:
        ctx = ssl.create_default_context()
        if not verify:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        conn = _PinnedHTTPS(parts.hostname, port, ip, timeout=timeout, context=ctx)
    else:
        conn = _PinnedHTTP(parts.hostname, port, ip, timeout=timeout)
    try:
        target = (parts.path or "/") + ("?" + parts.query if parts.query else "")
        conn.request("GET", target, headers={"User-Agent": UA, "Accept": "text/html,*/*;q=0.8",
                                             "Accept-Encoding": "identity", "Connection": "close"})
        resp = conn.getresponse()
        info = {"status": resp.status, "location": resp.getheader("Location"),
                "ctype": (resp.getheader("Content-Type") or "").lower(),
                "disp": (resp.getheader("Content-Disposition") or "").lower(), "body": "", "cert": None}
        if https and verify:
            try:
                cert = conn.sock.getpeercert()
                if cert:
                    nb = ssl.cert_time_to_seconds(cert["notBefore"])
                    issuer = dict(x[0] for x in cert.get("issuer", ()))
                    info["cert"] = {"age_days": (time.time() - nb) / 86400,
                                    "issuer": issuer.get("organizationName", issuer.get("commonName", "?"))}
            except Exception:  # noqa: BLE001
                pass
        # GUARDRAIL: the body is only ever read when ALL of these hold; payloads are never read, saved or run.
        is_download = "attachment" in info["disp"] or any(t in info["ctype"] for t in DOWNLOAD_TYPES)
        last_seg = parts.path.rsplit("/", 1)[-1]
        ext = last_seg.rsplit(".", 1)[-1].lower() if "." in last_seg else ""
        looks_like_file = ext in EXEC_EXT or ext in ARCHIVE_EXT
        texty = "html" in info["ctype"] or "text" in info["ctype"] or not info["ctype"]
        info["download"] = is_download
        info["unread"] = looks_like_file and not is_download and resp.status < 300
        info["disguised"] = None
        if not is_download and not looks_like_file and resp.status < 300 and texty:
            head = resp.read(16)
            info["disguised"] = sniff_binary(head)
            if not info["disguised"]:
                raw = head + resp.read(MAX_BODY - len(head))
                m = re.search(r"charset=([\w-]+)", info["ctype"])
                try:
                    info["body"] = raw.decode(m.group(1) if m else "utf-8", errors="replace")
                except LookupError:
                    info["body"] = raw.decode("utf-8", errors="replace")
        return info
    finally:
        conn.close()


def fetch(url, timeout, add, allow_private=False):
    """Follow redirects manually (each hop re-resolved and checked). Returns dict or None."""
    hops, cur = 0, url
    verify_failed = False
    while True:
        parts = urlsplit(cur)
        ips = resolve(parts.hostname)
        if is_private(ips) and not allow_private:
            add("generic", 3, "redirect or host resolves to a private/internal address (not fetched)")
            return None
        info = None
        for verify in ((True, False) if parts.scheme == "https" else (False,)):
            try:
                info = _fetch_hop(cur, ips[0], timeout, verify)
                break
            except ssl.SSLCertVerificationError as e:
                msg = (getattr(e, "verify_message", "") or str(e)).lower()
                if "self" in msg and "signed" in msg:
                    add("generic", 15, "TLS: self-signed certificate")
                elif "expired" in msg:
                    add("generic", 12, "TLS: expired certificate")
                elif "match" in msg or "hostname" in msg:
                    add("generic", 18, "TLS: certificate does not match the host name")
                elif "local issuer" in msg:
                    # usually a gap in this PC's root store (or a TLS-inspection proxy), not the site's fault
                    add("generic", 2, "TLS: issuer not in this PC's trust store (usually harmless)")
                else:
                    add("generic", 12, "TLS: certificate not trusted")
                verify_failed = True
        if info is None:
            return None
        if info["cert"] and info["cert"]["age_days"] < 7:
            add("generic", 6, "TLS certificate issued only %d day(s) ago" % info["cert"]["age_days"])
        if 300 <= info["status"] < 400 and info["location"]:
            nxt = urljoin(cur, info["location"])
            if urlsplit(nxt).scheme not in ("http", "https") or not urlsplit(nxt).hostname:
                return {"final_url": cur, "hops": hops, **info}
            hops += 1
            if hops > MAX_REDIRECTS:
                add("generic", 10, "redirect loop / more than %d redirects" % MAX_REDIRECTS)
                return {"final_url": cur, "hops": hops, **info}
            cur = nxt
            continue
        return {"final_url": cur, "hops": hops, "verify_failed": verify_failed, **info}


# --------------------------------------------------------------------------- page content checks
def content(html, final_url, add):
    low = html.lower()
    parts = urlsplit(final_url)
    host = (parts.hostname or "").lower()
    _, reg = split_host(host)
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = re.sub(r"\s+", " ", title_m.group(1)).strip() if title_m else ""

    has_pw = bool(re.search(r"<input[^>]+type\s*=\s*[\"']?password", low))
    if has_pw:
        add("phishing", 8, "page contains a password field")
        for m in re.finditer(r"<form[^>]+action\s*=\s*[\"']?([^\"'\s>]+)", low):
            action = urljoin(final_url, m.group(1))
            ah = (urlsplit(action).hostname or "").lower()
            if ah and split_host(ah)[1] != reg:
                add("phishing", 30, "form posts credentials to a different domain (%s)" % ah)
                break
            if action.startswith("http://") and parts.scheme == "https":
                add("phishing", 12, "login form submits over plain HTTP")
                break
    if re.search(r"<input[^>]+(name|id|placeholder|autocomplete)\s*=\s*[\"']?[^\"'>]*(cc-number|card[\s_-]*(number|no)|cvv|cvc|iban)", low):
        add("phishing", 15, "page asks for payment card / bank details")
    if reg not in TRUSTED:
        for brand, legit in BRANDS.items():
            if reg in legit or len(brand) < 5:
                continue
            if brand in title.lower():
                add("phishing", 30 if has_pw else 10,
                    "page title mentions '%s' but domain is not theirs%s" % (brand, " and asks for a password" if has_pw else ""))
                break
    if re.search(r"(account|card|profile).{0,40}(suspended|locked|limited|compromised)|verify your (identity|account)|unusual (sign-in|activity)", low):
        add("phishing", 10, "urgent account-suspension / verification wording")
    if re.search(r"(your (computer|device|pc) (is|has been) (infected|compromised))|virus (was )?detected|call (microsoft|apple) support|tech(nical)? support.{0,30}\d{3}", low):
        add("phishing", 30, "fake security-alert / tech-support scam wording")
    if re.search(r"oncontextmenu\s*=\s*[\"']?return false|event\.button\s*==\s*2", low):
        add("phishing", 6, "right-click disabled")

    # malware / dropper behaviour
    if (re.search(r"win(dows)?\s*\+\s*r", low) and re.search(r"ctrl\s*\+\s*v", low)) or \
            (re.search(r"clipboard\.writetext|execcommand\(['\"]copy", low) and re.search(r"powershell|mshta|cmd(\.exe)?\s*/c|curl\s+http", low)):
        add("malware", 45, "ClickFix-style lure: tells the user to paste a command into Run/terminal")
    if re.search(r"coinhive|coin-hive|cryptonight|webminepool|minero\.cc|crypto-loot", low):
        add("malware", 40, "cryptocurrency-miner script")
    if re.search(r"<iframe[^>]*(width\s*=\s*[\"']?[01][\"'\s>]|height\s*=\s*[\"']?[01][\"'\s>]|display\s*:\s*none|visibility\s*:\s*hidden)", low):
        add("malware", 20, "hidden iframe")
    obf = len(re.findall(r"eval\(|atob\(|unescape\(|fromcharcode|document\.write\(", low))
    if obf >= 6:
        add("malware", 18, "heavily obfuscated JavaScript (%d eval/atob/unescape calls)" % obf)
    elif obf >= 3:
        add("malware", 8, "some obfuscated JavaScript (%d eval/atob/unescape calls)" % obf)
    if len(re.findall(r"\\x[0-9a-f]{2}", low)) >= 60:
        add("malware", 12, "long hex-escaped JavaScript strings")
    m = re.search(r"<meta[^>]+http-equiv\s*=\s*[\"']?refresh[^>]+url\s*=\s*['\"]?([^'\"\s>]+)", low)
    if m:
        th = (urlsplit(urljoin(final_url, m.group(1))).hostname or "").lower()
        if th and split_host(th)[1] != reg:
            add("generic", 10, "meta-refresh redirect to another domain (%s)" % th)
    return title


# --------------------------------------------------------------------------- main entry point
def analyze(raw, opts=None):
    """Analyse one URL. opts: fetch (bool), rdap (bool), timeout (s), allow_private (tests only)."""
    opts = {"fetch": True, "rdap": True, "timeout": 8, **(opts or {})}
    t0 = time.time()
    res = {"input": raw, "url": None, "final_url": None, "verdict": "invalid", "category": "", "score": 0,
           "signals": [], "title": "", "status": None, "seconds": 0.0}
    url, guessed = normalize(raw)
    if not url:
        res["signals"] = [("generic", 0, "not a valid http(s) URL")]
        return res
    res["url"] = res["final_url"] = url
    signals, seen = [], set()

    def add(cat, weight, text):
        if text not in seen:
            seen.add(text)
            signals.append((cat, weight, text))

    parts = urlsplit(url)
    host = parts.hostname.lower()
    sub, reg = split_host(host)

    feed_hits = FEEDS.match(url, host, reg)
    for s in feed_hits:
        add(*s)
    lexical(url, add)
    if reg in TRUSTED and not feed_hits:
        add("good", -40, "well-known legitimate domain (%s)" % reg)

    ips = None
    try:
        ips = resolve(host)
    except OSError:
        add("generic", 10, "domain does not resolve (dead or not yet active)")

    if opts["rdap"] and ips and reg not in SHORTENERS and not re.fullmatch(r"[\d.:]+", host) and reg not in TRUSTED:
        age = domain_age_days(reg, opts["timeout"])
        if age is not None:
            if age < 14:
                add("generic", 25, "domain registered only %d day(s) ago" % age)
            elif age < 30:
                add("generic", 20, "domain registered %d days ago" % age)
            elif age < 90:
                add("generic", 8, "domain is young (%d days)" % age)
            elif age > 730:
                add("good", -8, "domain is established (%d years)" % (age // 365))

    if opts["fetch"] and ips:
        info = None
        try:
            info = fetch(url, opts["timeout"], add, opts.get("allow_private", False))
        except (OSError, http.client.HTTPException, ValueError) as e:
            if guessed and not isinstance(e, ssl.SSLCertVerificationError):
                try:
                    url = "http://" + url[len("https://"):]
                    res["url"] = res["final_url"] = url
                    info = fetch(url, opts["timeout"], add, opts.get("allow_private", False))
                except (OSError, http.client.HTTPException, ValueError):
                    pass
        if info:
            res["final_url"], res["status"] = info["final_url"], info["status"]
            if info["hops"] >= 3:
                add("generic", 8, "%d redirects before the final page" % info["hops"])
            fh = (urlsplit(info["final_url"]).hostname or "").lower()
            if fh and split_host(fh)[1] != reg:
                add("generic", 5, "redirects to another domain (%s)" % fh)
                lexical(info["final_url"], add, "after redirect: ")
                if split_host(fh)[1] in TRUSTED:
                    add("good", -10, "redirect lands on a well-known domain")
                for s in FEEDS.match(info["final_url"], fh, split_host(fh)[1]):
                    add(*s)
            if info.get("download"):
                add("malware", 30, "server answers with a file download (%s) - not read" % (info["ctype"] or "attachment").split(";")[0])
            if info.get("disguised") and info["disguised"] not in ("image", "PDF"):
                add("malware", 35, "server sends a %s disguised as a web page - dropped after 16 bytes" % info["disguised"])
            elif info.get("disguised"):
                add("generic", 3, "response is a %s, not a web page" % info["disguised"])
            if info.get("unread"):
                add("generic", 0, "URL points to a file: body deliberately not read")
            if info["body"]:
                res["title"] = content(info["body"], info["final_url"], add)
            if info["status"] >= 400:
                add("generic", 3, "HTTP %d" % info["status"])

    res["signals"], res["seconds"] = signals, round(time.time() - t0, 2)
    return rescore(res)


def rescore(res, extra=()):
    """(Re)compute score and verdict from res['signals'] plus any extra signals."""
    signals = list(res["signals"]) + list(extra)
    total = max(0, min(100, sum(w for _, w, _ in signals)))
    p = sum(w for c, w, _ in signals if c == "phishing")
    m = sum(w for c, w, _ in signals if c == "malware")
    if total >= 60:
        verdict = "malware" if m > p else "phishing"
    elif total >= 30:
        verdict = "suspicious"
    else:
        verdict = "clean"
    res.update(verdict=verdict, score=total, category="malware" if m > p else "phishing",
               signals=sorted(signals, key=lambda s: -abs(s[1])))
    return res


# --------------------------------------------------------------------------- VirusTotal IOC lookups
# Read-only lookups by URL id / hash: nothing is submitted for scanning and no file is ever downloaded.
# The API key is never stored: it comes from the VT_API_KEY environment variable or the GUI session.
HASH_RE = re.compile(r"^(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$")
VT_BASE = "https://www.virustotal.com/api/v3/"


class VTLimiter:
    """Spaces requests out to respect the API quota (free key: 4 requests/minute, 500/day)."""

    def __init__(self, per_minute=4):
        self.interval, self._next, self._lock = 60.0 / per_minute, 0.0, threading.Lock()

    def set_rate(self, per_minute):
        self.interval = 60.0 / max(1, per_minute)

    def wait(self, stop=None):
        with self._lock:
            now = time.time()
            slot = max(now, self._next)
            self._next = slot + self.interval
        while time.time() < slot:
            if stop is not None and stop.is_set():
                return False
            time.sleep(0.25)
        return True


VT_LIMITER = VTLimiter(4)


def vt_url_id(url):
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")


def vt_gui_url(item):
    """Browser link for the user to open themselves (VirusTotal GUI addresses URLs by sha256)."""
    if HASH_RE.match(item):
        return "https://www.virustotal.com/gui/file/" + item.lower()
    return "https://www.virustotal.com/gui/url/" + hashlib.sha256(item.encode()).hexdigest()


def vt_get(path, key, timeout=20, stop=None):
    """-> (http_status, parsed_json_or_None). Status 0 = network error / cancelled."""
    if not VT_LIMITER.wait(stop):
        return 0, None
    try:
        req = urllib.request.Request(VT_BASE + path, headers={"x-apikey": key, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:  # noqa: BLE001
        return 0, None


def _vt_stats_signal(stats, names, what):
    mal, sus = stats.get("malicious", 0), stats.get("suspicious", 0)
    total = sum(v for v in stats.values() if isinstance(v, int))
    blob = " ".join(names).lower()
    cat = "phishing" if re.search(r"phish|fraud|scam", blob) else "malware"
    if mal >= 5:
        return [(cat, 80, "VirusTotal: %d/%d engines flag this %s as malicious" % (mal, total, what))]
    if mal >= 1 or sus >= 3:
        return [("generic", 35, "VirusTotal: %d malicious + %d suspicious of %d engines (%s)" % (mal, sus, total, what))]
    if total >= 40:
        return [("good", -5, "VirusTotal: 0 of %d engines flag this %s" % (total, what))]
    return []


def vt_lookup_hash(h, key, stop=None):
    """-> {"signals": [...], "name": str|None, "note": str|None}"""
    status, data = vt_get("files/" + h.lower(), key, stop=stop)
    if status == 200 and data:
        a = data["data"]["attributes"]
        label = (a.get("popular_threat_classification") or {}).get("suggested_threat_label")
        names = [label or ""] + [n["value"] for n in (a.get("popular_threat_classification") or {}).get("popular_threat_name", [])[:3]]
        sig = _vt_stats_signal(a.get("last_analysis_stats", {}), names, "file")
        if label:
            sig.append(("generic", 0, "VirusTotal threat label: " + label))
        return {"signals": sig, "name": a.get("meaningful_name"), "note": None}
    return {"signals": [], "name": None, "note": _vt_note(status, "hash")}


def vt_lookup_url(url, key, stop=None):
    """-> {"signals": [...], "sha256": str|None, "note": str|None}. 404 means VT has no record (we do NOT submit it)."""
    status, data = vt_get("urls/" + vt_url_id(url), key, stop=stop)
    if status != 200 or not data:
        return {"signals": [], "sha256": None, "note": _vt_note(status, "URL")}
    a = data["data"]["attributes"]
    names = list((a.get("threat_names") or [])) + [str(v) for v in (a.get("categories") or {}).values()]
    sig = _vt_stats_signal(a.get("last_analysis_stats", {}), names, "URL")
    sha = a.get("last_http_response_content_sha256")
    if sha:
        # VirusTotal already fetched and hashed the payload for us - an IOC we can read without downloading anything
        sig.append(("generic", 0, "payload sha256 (from VirusTotal, not downloaded here): " + sha))
        if any(c in ("malware", "phishing") for c, w, _ in sig if w > 0):
            sub = vt_lookup_hash(sha, key, stop)
            sig.extend(s for s in sub["signals"] if s[1] == 0)
    return {"signals": sig, "sha256": sha, "note": None}


def _vt_note(status, what):
    return {404: "VirusTotal has no record of this %s (not submitted)" % what,
            401: "VirusTotal rejected the API key", 403: "VirusTotal rejected the API key",
            429: "VirusTotal quota exceeded - try later or lower the requests/min",
            0: "VirusTotal lookup failed (network) or was cancelled"}.get(status, "VirusTotal HTTP %d" % status)
