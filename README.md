# AMS Quick Scheduler

<p align="center">
  <img src="logo.jpg" alt="AMS Quick Scheduler Logo" width="300" style="border-radius: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
</p>

A fast, offline-ready personal scheduler for the **2027 AMS 107th Annual Meeting** (American Meteorological Society). 

## ✨ Features

- **⚡ Fast**: Instant full-text search across all 4,500+ presentation titles, abstracts, authors, and rooms.
- **🔒 Local Storage**: The schedule is saved in browser's local storage and can be backed up as a simple `my_schedule.json` file.
- **🔗 Add by Link**: Paste any AMS Confex presentation or session URL / ID (e.g. `Paper/493311` or `Session/76055`) and the app gets needed information from the website automatically. This is helpful to adapt to last minute changes.
- **📅 Multiple Export Options**: HTML, PDF, JSON, ICS calendar, AI prompt
- **📱 Mobile-Friendly**: The webpage and the exported HTML file are mobile friendly on smartphones, tablets, etc.

## 🚀 Usage

### 1. Launch the App
In this folder, run:
```bash
python3 app.py
```
This automatically starts a lightweight local server and opens `http://localhost:8080/` in your default browser.

### 2. Use via GitHub Pages
Anyone can visit the GitHub Pages site associated with the repo/fork to build their schedule in the browser, and the schedule is stored strictly locally.    
Example: https://guoqing-noaa.github.io/ams_quick_scheduler/

## 🔄 Updating Data in the Final Days

If speakers withdraw or room numbers change right before the meeting, simply run:
```bash
python3 fetch_ams_program.py --meeting 107ANNUAL
```
- Takes ~15–20 seconds to fetch the entire fresh conference dataset from the Confex API.
- The custom schedule **remains completely intact** because it references stable IDs.
- Any withdrawn talks or room changes will immediately display warning banners in the schedule view.

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
