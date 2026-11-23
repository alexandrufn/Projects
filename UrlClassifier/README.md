# URL Classifier

Desktop app (Python + tkinter, **no extra dependencies**) that takes many URLs at once and classifies each as
**clean**, **suspicious**, **phishing** or **malware**, with the evidence behind every verdict.

## Run

Double-click `run.bat`, or `python app.py`. Python 3.10+.

1. Paste URLs (one per line) or use **Load file…**. Defanged input (`hxxp://evil[.]com`) works.
2. Press **Analyze**. Results stream into the table as they finish; click a row for the full signal list.
3. **Export CSV…** saves everything. Right-click a row to copy the URL defanged.

Optional: **Update feeds** downloads the OpenPhish and URLhaus blocklists into `data/feeds/` for exact-URL matching.

## Why it is fast

Analysis is network-bound (DNS, TLS, HTTP), so each URL runs in a thread-pool worker (default 24, up to 64).
Waiting on one slow site never blocks the rest. A per-domain cache avoids repeat lookups.
This beats one-process-per-URL or LLM agents: no startup cost, no tokens, and fully offline-capable scoring.

## What it checks (weighted signals, summed to a 0-100 score)

| Group | Examples |
|-------|----------|
| URL structure | raw/obfuscated IP, `user@host` trick, punycode, long URL, nested subdomains, random-looking names, risky TLDs, shorteners, non-standard ports, executable extensions |
| Brand impersonation | lookalikes (`paypa1`), brand name in an unrelated domain, brand in page title |
| Reputation | OpenPhish / URLhaus feed matches, domain age via RDAP, well-known domain allowlist |
| Network | DNS resolution, TLS errors (self-signed, expired, hostname mismatch), brand-new certificate, redirect chains |
| Page content | password form posting to another domain, card/bank fields, scam wording, hidden iframes, obfuscated JS, crypto miners, ClickFix "paste this command" lures, file-download responses |

Verdict: score < 30 clean, 30-59 suspicious, 60+ phishing or malware (whichever signal group weighs more).

## VirusTotal / hash IOCs

Tick **VirusTotal IOC lookup** and enter an API key (or set the `VT_API_KEY` environment variable; the key is held in memory only and never written to disk).

- Each URL is looked up **read-only** by its URL id. Nothing is submitted for scanning, and unknown URLs just report "no record".
- If VirusTotal already fetched the URL's payload, its **sha256 is shown as an IOC** (and its detection label is looked up) - so you get the hash without downloading anything.
- You can paste **file hashes** (MD5 / SHA-1 / SHA-256) straight into the input box to get their verdicts.
- Requests are rate-limited (default 4/min = free-key quota; raise it for a premium key). By default only non-clean URLs are looked up to save quota.
- Right-click a row: *Open on VirusTotal*, *Open payload sha256 on VirusTotal*, or *Search the web for this IOC* (opens your browser on a search for the domain/hash to find blog posts and reports).

## Guardrails (enforced in code, checked by `python -m unittest test_guardrails -v`)

- **Nothing is executed.** No `subprocess`, `eval`, `exec`, `ctypes` etc. anywhere; a test scans the source and fails if one appears.
- **No payload is downloaded or saved.** The only files written are the blocklist feeds (on *Update feeds*) and your CSV export.
  - Responses marked as downloads/attachments, or whose URL ends in a file extension (`.exe`, `.zip`, `.js`, `.iso`, ...), are never read.
  - Text-labelled responses are checked after only 16 bytes; if they start like an EXE, ZIP, PDF, ELF, script etc., the connection is dropped (flagged as *disguised binary*).
  - Page text is capped at 400 KB, decoded as plain text, scanned with regexes, never rendered, and discarded.
- **Passive mode:** untick *Contact URLs* and the app never connects to the target at all (URL structure, feeds, RDAP and VirusTotal only).
- Hosts resolving to private/internal addresses are not fetched; redirects are re-checked at every hop and the connection is pinned to the checked IP.
- Privacy: domain-age lookups send the registrable domain to `rdap.org`; VirusTotal lookups send the URL/hash to VirusTotal. Untick either to avoid that.
- Fetching a hostile site still reveals your IP to it. For serious triage use passive mode or an isolated network.

This is a heuristic triage aid, not a replacement for a commercial scanner: expect false positives and misses (cloaked or very new sites).
