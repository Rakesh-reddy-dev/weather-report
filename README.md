# TerraPulse — Environmental Intelligence Dashboard

TerraPulse is a Python desktop application built with CustomTkinter. It combines a themed environmental overview, live weather lookup, demo climate charts, CSV exploration, threshold rules, and report exports.

## Features

- Midnight Forest dark theme and custom sidebar navigation
- Overview dashboard with clearly labeled illustrative sample values
- Live current-weather lookup through Open-Meteo (internet required)
- Climate trend charts using Matplotlib
- CSV import and numeric summaries using Pandas
- User-configured temperature threshold evaluation
- Export status reports as TXT and latest weather readings as JSON

## Important data notes

- Overview and climate analytics chart values are **illustrative demo data**, not real measurements.
- Weather Explorer fetches current weather data from Open-Meteo when online.
- Air quality is not measured by this application.
- Threshold checks are user-configured examples, not official alerts or emergency guidance.

## Requirements

- Windows 10/11, macOS, or Linux
- Python 3.10 or newer recommended
- Internet connection only for live weather lookup

## Run in VS Code

1. Download or clone this repository.
2. Open the `TerraPulse` folder in VS Code.
3. Open **Terminal → New Terminal**.
4. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

5. Activate it on Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt:

   ```bat
   .venv\Scripts\activate.bat
   ```

6. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

7. Run:

   ```bash
   python main.py
   ```

## Build a Windows executable (optional)

Install PyInstaller:

```bash
python -m pip install pyinstaller
```

Build:

```bash
python -m PyInstaller --noconfirm --clean --windowed --onefile --name TerraPulse main.py
```

The executable will be created in the `dist` folder. Test it on your own Windows machine before publishing a release.

## GitHub upload

Upload the contents of this project folder to a new public GitHub repository named `TerraPulse`. Do not upload `.venv`, `__pycache__`, or personal data.

For a release, create a GitHub Release with a version tag such as `v1.0.0`. If you build the Windows executable, attach `dist/TerraPulse.exe` to that release. Include the source code ZIP automatically provided by GitHub.

## Data source

Live weather uses the Open-Meteo geocoding and forecast APIs:
- https://geocoding-api.open-meteo.com/
- https://api.open-meteo.com/

Review the provider's current terms and attribution requirements before distributing the app.

## License

Choose a license before public distribution. MIT is a common option for student projects; add a `LICENSE` file if you choose it.
