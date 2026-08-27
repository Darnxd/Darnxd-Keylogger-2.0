
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

 - ## **Libraries**

| Library             | Purpose                        | Why Needed                                                                 |
|---------------------|--------------------------------|----------------------------------------------------------------------------|
| **pynput**          | Keyboard and mouse capture     | Provides low‑level input event listeners. Cross‑platform alternative to Win32 API hooks. |
| **Pillow (PIL)**    | Screenshot capture             | `ImageGrab.grab()` captures full screen. Required for screenshot module.   |
| **threading**       | Multi‑threaded architecture    | Each module (keyboard, mouse, screenshot, credential scanner, compression) runs in its own thread. |
| **queue**           | Real‑time event bus            | Thread‑safe communication between capture modules and dashboard display.   |
| **re**              | Credential pattern matching    | Regex patterns for detecting emails, passwords, SSNs, etc.                 |
| **csv**             | Credential storage             | Writes harvested credentials to structured CSV format.                     |
| **json**            | Internal event serialization   | Used internally, not for output.                                           |
| **zipfile**         | Evidence compression           | Bundles all artifacts into ZIP archives.                                   |
| **pathlib**         | File path management           | Clean cross‑platform path handling.                                        |
| **datetime**        | Timestamps                     | Every event is timestamped in ISO format.                                  |
| **collections.deque** | Live event feed (circular buffer) | Keeps last N events for dashboard display.                                |
| **socket**          | Future exfiltration support    | Placeholder for TCP exfil, imported but not actively used.                  |
| **os**              | Screen clearing                | Clears console (`cls` on Windows, `clear` on Linux/macOS).                 |

 - ## **Operating Systems**

   - Windows (fully tested)
   - Linux (tested on Kali, Ubuntu)
   - macOS (should work, limited testing)

# **⚙️ System Workflow (End‑to‑End)**

   - **User Input**
    
        - A user types keystrokes or performs mouse actions on the system.        
        - Example: typing Abc123456@gmail.com or clicking on a file.
        
   - **KeystoneCaptor (Keyboard Module)**
     
        - Captures raw keystrokes in bracket notation ([backspace], [ctrl]a, [enter]).        
        - Sends events to the SequenceBuilder.
          
  - **SequenceBuilder**
    
       - Builds two streams:
           - Raw sequence → verbatim keystrokes.
           - Decoded text → applies backspaces, spaces, enters.
       - Example: raw = admin[backspace]gmail.com, decoded = admingmail.com.

   - **MouseDetector (Mouse Module)**

       - Logs clicks with button type, coordinates, and zone (TOP‑LEFT, TOP‑RIGHT, etc.).
       - Samples every 5th movement to reduce noise.

   - **ScreenshotCaptor (Screenshot Module)**

        - Takes full‑screen screenshots every 30 seconds.
        - Stores PNG files in Darnxd/screenshots/.

   - **CredentialHarvester (Regex Engine)**

        - Scans decoded text every 3 seconds.
        - Extracts real credentials (emails, usernames, passwords, tokens, SSNs, credit cards, phone numbers).
        - Saves matches in plaintext to HARVESTED_CREDENTIALS.csv.

   - **HarvestStore (CSV Storage)**

        - Immediately logs each credential with:
            - Timestamp
            - Type (EMAIL, PASSWORD, etc.)
            - Value (plaintext)
            - Context snippet

   - **EvidenceBuffer (Event Store)**

        - Thread‑safe buffer that tracks counts: keystrokes, clicks, screenshots, credentials, bundles.
        - Feeds data to the live CLI dashboard. 

   - **Bundler (Compression)**

        - Every 2 minutes, compresses all evidence (CSV, screenshots, reports) into a ZIP archive.
        - Creates a final bundle on exit.

   - **Exfiltration Marker**

      - Generates EXFILTRATION_MARKER.txt to simulate staged exfiltration.
      - No real network transmission — lab‑only simulation.

   - **Report Generator (DarnxdReport)**

      - Produces a structured forensic report (darnxd_keylogger_report.txt).
      - Includes ASCII banner, evidence summary, keystroke analysis, credential dump, mouse activity, screenshot log.
    
# **🛠️ Local Setup**

   ### Installation Method
          pip install pynput pillow
          
   ### Requirements

   -   Python 3.8 or higher
   - Administrator/root privileges (required for global key capture on some systems)

   ## Step‑by‑Step Setup

   1. Clone or download the script
      
            git clone https://github.com/darnxd/darnxd-keylogger-2.0.git
            cd darnxd-keylogger-2.0
   2. Create a virtual environment (Recommended) 

            python -m venv venv
      For Linux/Mac
      
           source venv/bin/activate   # Linux/macOS
      For Windows

          venv\Scripts\activate      # Windows

   3. Install dependencies
      
            pip install pynput pillow

   4.  Run the script (works on Windows)

            python darnxd_keylogger_2.0.py

   5. Run the Script (works on Linux/MacOS)
      
            python3 darnxd_keylogger_2.0.py

## **Run Without Installing (One-liner)**

      pip install pynput pillow && python darnxd_keylogger_2.0.py


# **📸 Screenshots**

