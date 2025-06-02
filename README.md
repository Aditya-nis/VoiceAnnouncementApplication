
📢 Voice Announcement Application - Readme
================================================================================

A desktop-based Voice Announcement System designed for use in public places like railway stations, bus stands, schools, or institutions, developed in Python with PyQt5 for a modern graphical interface. This application allows live microphone announcements, text-to-speech (TTS) based voice announcements, scheduled announcements, background chimes, and advertisement audio management — all within a clean, intuitive GUI.

📖 Project Description
================================================================================
The Voice Announcement Application is a powerful and versatile desktop-based public announcement system developed in Python with PyQt5. It is thoughtfully designed for use in a wide range of public venues such as railway stations, bus terminals, airports, schools, colleges, offices, hospitals, and other institutions where regular voice announcements are necessary for informing, guiding, or notifying people.

This application offers an intuitive, modern graphical user interface, making it exceptionally easy for operators to manage announcements, even without advanced technical knowledge. The software provides multiple modes of announcements, catering to both manual and automated requirements. Users can make live microphone announcements in real-time or use the Text-to-Speech (TTS) feature to instantly convert typed text into clear, audible announcements. Additionally, it supports scheduled announcements, allowing operators to automate important messages that need to be broadcast at specific times of the day. This ensures timely delivery of information without continuous operator involvement.

An essential feature of this application is the option to play background chime sounds before each announcement, enhancing the audibility and attention factor in noisy public environments. The system also offers support for background advertisement audio playback, which can be played during idle times, making it ideal for commercial venues seeking to manage promotional audio content alongside regular announcements.

To maintain operational transparency and administrative control, the Voice Announcement Application keeps detailed logs of all announcements. These logs record essential information like the type of announcement, content, and timestamp, and can be exported in CSV, TXT, or PDF formats for record-keeping and reporting purposes.

The application comes with useful features like dark and light theme support, customizable volume control for both TTS and background audio, and a built-in advertisement management module. It is a fully offline, lightweight desktop solution, ensuring reliable performance even in areas with limited or no internet connectivity. Future upgrades may include remote scheduling via API, cloud database integration, multilingual TTS support, and enhanced dashboard analytics, making this application a scalable solution for evolving public announcement needs.




🎯 Features
================================================================================

- Live Microphone Announcements
- Text-to-Speech (TTS) Announcements
- Scheduled Announcement Management
- Background Chime Playback before Announcements
- Announcement Logs with Export (CSV, TXT, PDF)
- Dark and Light Theme Support
- Volume Control for TTS and Background Audio
- Export Announcement Logs
- Advertisement Audio Management (optional)
- Clean, User-friendly PyQt5 GUI
- Log Search, Sort and Filter Functionality
- Announcement Queue Preview
- Play/Stop Chimes or Background Audio
- Configuration via JSON File

🛠️ System Requirements
================================================================================

- Operating System: Windows 10/11 (64-bit)
- Python Version: 3.9+
- Text-to-Speech Engine: pyttsx3 (offline) or gTTS (optional)
- PyQt5: for the GUI
- Database: SQLite (or optional SQL Server integration)

📦 Python Dependencies
================================================================================

Install all dependencies using:

    pip install -r requirements.txt

Contents of requirements.txt:

    PyQt5==5.15.10
    pyttsx3==2.90
    pandas==2.2.2
    openpyxl==3.1.2
    reportlab==4.1.0
    tqdm==4.66.2
    Pillow==10.3.0
    python-docx==1.1.0
    tabulate==0.9.0
    playsound==1.3.0

📥 Installation Guide
================================================================================

1. Install Python 3.9 or higher from https://www.python.org/downloads/
2. Install required dependencies:

       pip install -r requirements.txt

3. Verify installation by running:

       python --version
       pip list

4. Start the application:

       python voice_announcement_app.py

🖥️ How It Works
================================================================================

- **Live Mic Announcements:** Press the 'Mic' button and speak — announcements broadcast live.
- **Text Announcements:** Type your message → click 'Announce' — TTS reads it out.
- **Scheduled Announcements:** Add announcements with future date and time — app auto-plays them.
- **Chime Sounds:** Chime plays automatically before each announcement (configurable).
- **Background Audio:** Loop background ads/audio during idle time (optional).
- **Logs:** All announcements and activities logged to database with export options.

📁 Project Structure
================================================================================

/voice-announcement-app/
│
├── main.py                      # Main Application Script
├── ui/
│   └── main_window.ui           # PyQt5 UI File (optional)
├── assets/
│   ├── chimes/
│   ├── ads/
│   └── icons/
├── database/
│   └── announcement_logs.db     # SQLite Database
├── reports/
│   └── logs/
├── config.json                  # Application Configurations
├── requirements.txt
└── Voice_Announcement_Application_Readme.txt

📑 Example Announcement Log Export (CSV)
================================================================================

| ID | Type        | Message                  | DateTime            | Status    |
|----|-------------|--------------------------|---------------------|-----------|
| 1  | Mic         | N/A                      | 2025-06-01 10:30:00 | Completed |
| 2  | TTS         | "Train No 12034 arriving" | 2025-06-01 11:00:00 | Completed |
| 3  | Scheduled   | "Platform 3 attention"    | 2025-06-01 11:15:00 | Pending   |

================================================================================
🗓️ Example Scheduled Announcements JSON
================================================================================

[
  {
    "id": 1,
    "message": "Train no 12034 is arriving at platform 1.",
    "date": "2025-06-01",
    "time": "10:30:00",
    "status": "Pending"
  },
  {
    "id": 2,
    "message": "Train no 14321 has been delayed.",
    "date": "2025-06-01",
    "time": "11:00:00",
    "status": "Pending"
  }
]

💾 Database Details (if using SQLite)
================================================================================

Database Name: announcement_logs.db

Tables:
- Announcements
  - ID (Primary Key)
  - Type (Mic / Text / Scheduled)
  - Message
  - DateTime
  - Status

📜 Sample config.json
================================================================================

{
    "tts_voice": "default",
    "volume": 1.0,
    "theme": "dark",
    "database_path": "database/announcement_logs.db",
    "chime_sound": "assets/chimes/chime.wav"
}

🐞 Known Issues & Limitations
================================================================================

- TTS voice selection may vary depending on OS voice availability.
- Only tested on Windows (Linux/Mac compatibility unverified).
- Scheduled announcements work based on system time — ensure correct time settings.
- Background audio management requires supported audio format (.wav, .mp3).
- No real-time network announcement sync in current version (planned in future).
- Limited to one mic input source at a time.

📬 Support & Contact
================================================================================

Developer: Nisargandh Aditya Mahendra  
Email: adityanisargandh01@gmail.com  

For any issues, queries, or feature requests — feel free to reach out!

📝 License
================================================================================

This project is licensed under the MIT License.  
You are free to use, modify, and distribute this application.

🚀 Future Improvements
================================================================================

- API-based remote announcement scheduling.
- Multiple language TTS support.
- Advanced dashboard for announcements and statistics.
- Background advertisement audio with play limit management.
- Cloud database support (SQL Server / MySQL / Firebase).
- Auto-announcement of dynamic data via API (train/bus timings)
- Audio fade-in/out and sound effect transitions.
- Customizable GUI themes (multi-color options).
- User authentication for admin-only features.
- Playback queue view and audio preview options.

📸 Screenshots (Optional)
================================================================================
![picture 1](https://github.com/user-attachments/assets/1a843662-81b6-41e9-a429-617cb2dabb4e)
![picture 2](https://github.com/user-attachments/assets/a8946caa-1b15-4e9d-af66-841d43b9cb4f)
![picture 3](https://github.com/user-attachments/assets/d9dbe819-7d7d-408e-bb04-40aba838a195)

![picture 4](https://github.com/user-attachments/assets/c4ccf8a6-2e71-4c5a-8779-653b06b6bed1)
![picture 5](https://github.com/user-attachments/assets/edadee2d-9bee-4855-9d0c-c2c277d0017e)


📄 Third-Party Dependencies Licenses
================================================================================

This application uses open-source libraries under their respective licenses:
- PyQt5: GPL/LGPL
- pyttsx3: MIT
- pandas, openpyxl, reportlab: BSD/MIT
- Other Python packages: BSD/MIT/GPL compatible

================================================================================
