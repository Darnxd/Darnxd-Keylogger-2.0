# Darnxd-Keylogger-2.0

## ⚠️ Legal Disclaimer — READ THIS FIRST

   - This tool captures real keystrokes, passwords, emails, tokens, and screenshots from the machine it runs on.
   - Use ONLY on systems you own or have explicit written permission to test.
   - **Unauthorized** use is illegal and violates computer fraud laws.
   - The **author** assumes zero liability for misuse.
   - This is a security research and education tool.
   - Destroy all captured data immediately after authorized use.

# What Is This?
**Keylogger Darnxd 2.0** is a project I built for myself as part of my cybersecurity learning journey. It is an educational lab tool that show how attackers can capture keystrokes, mouse activity, screenshots, and credentials,and how forensic analysts can study this data. It automatically generates a forensic report (`darnxd_keylogger_report.txt`) and a credential log
(`HARVESTED_CREDENTIALS.csv`) to help students understand the risks of keyloggers. This project is strictly for authorized penetration testing labs and digital forensics practice, not for misuse. 

 **For example** typing "hello world" will appear in the log as `[h][e][l][l][o][space][w][o][r][l][d]`, and mouse clicks are recorded with timestamp and zone details and screenshots are taken every 30 seconds to show what was on the screen at that time.

This project is strictly for authorized penetration testing labs and digital forensics practice, not for misuse.

# 🧠 Architecture

      [KeystoneCaptor → Keyboard Capture]
                      ↓
      [MouseDetector → Mouse Clicks / Moves]
                      ↓
      [ScreenshotCaptor → Periodic Screenshots]
                      ↓
      [CredentialHarvester → Regex Scanning]
                      ↓
      [HarvestStore → CSV Credential Storage]
                      ↓
      [EvidenceBuffer → Thread‑safe Event Store]
                      ↓
      [Bundler → Compression + Exfil Marker]
                      ↓
      [Report Generator → Structured Forensic Report]

# **⚙️ Features**

### **Detection**

   - Keystroke sequence capture (raw bracket format logging)

   - Mouse click and movement detection with coordinates and zones

   - Periodic screenshot capture (every 30 seconds)

   - Regex‑based credential harvesting (emails, usernames, passwords, tokens)

   - Simple anomaly hooks (e.g., repeated failed logins, suspicious text patterns)

### **Response**

   - Evidence compression into ZIP bundles every 2 minutes

   - Exfiltration staging marker (EXFILTRATION_MARKER.txt)

   - Live CLI dashboard for real‑time monitoring of keys, clicks, creds, screenshots

   - Structured forensic report generation (.txt)

### **Analyst Experience**

   - Severity distribution of captured events (Low, Medium, High, Critical)

   - Top harvested credentials and activity summary

   - Incident board style forensic report with keystrokes, mouse logs, screenshots

   - Alert views for keystrokes, mouse activity, screenshots, and harvested data


# **🛠️ Technologies Used**

   - Python 3.8+

 **Libraries**
 Library	Version	Purpose	Why Needed
pynput	Latest	Keyboard and mouse capture	Provides low-level input event listeners. Alternative would be ctypes + Win32 API hooks, but pynput is cross-platform
Pillow (PIL)	Latest	Screenshot capture	ImageGrab.grab() captures the full screen. Required for the screenshot module
threading	stdlib	Multi-threaded architecture	Each module (keyboard, mouse, screenshot, credential scanner, compression) runs in its own thread
queue	stdlib	Real-time event bus	Thread-safe communication between capture modules and the dashboard display
re	stdlib	Credential pattern matching	All regex patterns for detecting emails, passwords, SSNs, etc.
csv	stdlib	Credential storage	Writes harvested credentials to structured CSV format
json	stdlib	Internal event serialization (not used for output)	—
zipfile	stdlib	Evidence compression	Bundles all artifacts into ZIP archives
pathlib	stdlib	File path management	Clean cross-platform path handling
datetime	stdlib	Timestamps	Every event is timestamped with ISO format
collections.deque	stdlib	Live event feed (circular buffer)	Keeps last N events for dashboard display
socket	stdlib	Future exfiltration support (not actively used)	Imported but not called — placeholder for TCP exfil
os	stdlib	Screen clearing	cls on Windows, clear on Linux/macOS for dashboard



