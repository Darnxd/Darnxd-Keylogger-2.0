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

# **✨ Features**
