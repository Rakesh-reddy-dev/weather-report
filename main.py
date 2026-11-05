import json
import threading
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    import customtkinter as ctk
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import pandas as pd
except ImportError as exc:
    raise SystemExit(
        f"Missing dependency: {exc}\n"
        "Run: python -m pip install customtkinter matplotlib pandas"
    )

APP_NAME = "TerraPulse"
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Midnight Forest palette
BG = "#071410"
SIDEBAR = "#0B1F18"
CARD = "#102820"
CARD_ALT = "#15352A"
ACCENT = "#54F2A1"
ACCENT_2 = "#29C7AC"
TEXT = "#E8F5EE"
MUTED = "#8FA99A"
WARNING = "#FFBF69"
RED = "#FF7777"
SKY = "#8AD7FF"

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
    56: "Freezing drizzle", 57: "Heavy freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Heavy freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light showers", 81: "Showers", 82: "Violent showers",
    85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm, hail", 99: "Thunderstorm, heavy hail",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


class TerraPulseApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TerraPulse | Environmental Intelligence")
        self.geometry("1360x850")
        self.minsize(1120, 720)
        self.configure(fg_color=BG)

        self.city_var = tk.StringVar(value="Vijayawada")
        self.status_var = tk.StringVar(value="Ready • Sample data loaded")
        self.last_weather = None
        self.active_page = "Overview"
        self.nav_buttons = {}
        self._build_shell()
        self.show_page("Overview")
        self._tick_clock()

    # ------------------------------------------------------------------ shell
    def _build_shell(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=235, corner_radius=0, fg_color=SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=22, pady=(27, 24))
        ctk.CTkLabel(brand, text="◈", font=ctk.CTkFont(size=30, weight="bold"),
                     text_color=ACCENT).pack(side="left", padx=(0, 10))
        title_frame = ctk.CTkFrame(brand, fg_color="transparent")
        title_frame.pack(side="left")
        ctk.CTkLabel(title_frame, text="TerraPulse", font=ctk.CTkFont(size=21, weight="bold"),
                     text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="ENVIRONMENTAL INTELLIGENCE",
                     font=ctk.CTkFont(size=8, weight="bold"), text_color=MUTED).pack(anchor="w")

        ctk.CTkLabel(self.sidebar, text="WORKSPACE", text_color="#648476",
                     font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w", padx=24, pady=(0, 9))
        for name, icon in [
            ("Overview", "◫"), ("Weather Explorer", "☼"), ("Climate Analytics", "⌁"),
            ("Data Lab", "▤"), ("Alert Center", "⚑"), ("Reports", "▧"), ("Settings", "⚙")
        ]:
            btn = ctk.CTkButton(
                self.sidebar, text=f"  {icon}    {name}", anchor="w", height=42,
                corner_radius=10, fg_color="transparent", hover_color=CARD_ALT,
                text_color=TEXT, font=ctk.CTkFont(size=13),
                command=lambda n=name: self.show_page(n)
            )
            btn.pack(fill="x", padx=13, pady=3)
            self.nav_buttons[name] = btn

        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)
        ctk.CTkFrame(self.sidebar, height=1, fg_color="#1C3B2E").pack(fill="x", padx=18, pady=12)
        ctk.CTkLabel(self.sidebar, text="DATA SOURCE", text_color="#648476",
                     font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w", padx=24)
        ctk.CTkLabel(self.sidebar, text="Open-Meteo API\nLocal CSV datasets",
                     justify="left", text_color=MUTED,
                     font=ctk.CTkFont(size=11)).pack(anchor="w", padx=24, pady=(7, 20))

        self.main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        self.topbar = ctk.CTkFrame(self.main, fg_color=BG, corner_radius=0, height=76)
        self.topbar.grid(row=0, column=0, sticky="ew", padx=30, pady=(19, 5))
        self.topbar.grid_columnconfigure(0, weight=1)
        self.page_title = ctk.CTkLabel(self.topbar, text="Environmental Overview",
                                       font=ctk.CTkFont(size=27, weight="bold"), text_color=TEXT)
        self.page_title.grid(row=0, column=0, sticky="w")
        self.clock_label = ctk.CTkLabel(self.topbar, text="", text_color=MUTED,
                                        font=ctk.CTkFont(size=12))
        self.clock_label.grid(row=0, column=1, sticky="e", padx=(10, 0))

        self.content = ctk.CTkScrollableFrame(self.main, fg_color=BG, corner_radius=0)
        self.content.grid(row=1, column=0, sticky="nsew", padx=30, pady=(0, 10))
        self.content.grid_columnconfigure(0, weight=1)

        footer = ctk.CTkFrame(self.main, fg_color=SIDEBAR, corner_radius=0, height=30)
        footer.grid(row=2, column=0, sticky="ew")
        ctk.CTkLabel(footer, textvariable=self.status_var, text_color=MUTED,
                     font=ctk.CTkFont(size=10)).pack(side="left", padx=18, pady=7)
        ctk.CTkLabel(footer, text="TERRAPULSE  •  LOCAL-FIRST ENVIRONMENTAL TOOL",
                     text_color="#648476", font=ctk.CTkFont(size=9, weight="bold")).pack(side="right", padx=18)

    def _tick_clock(self):
        self.clock_label.configure(text=datetime.now().strftime("%a, %d %b %Y   •   %I:%M:%S %p"))
        self.after(1000, self._tick_clock)

    def clear_content(self):
        for child in self.content.winfo_children():
            child.destroy()

    def show_page(self, page):
        self.active_page = page
        for name, button in self.nav_buttons.items():
            button.configure(fg_color=CARD_ALT if name == page else "transparent",
                             text_color=ACCENT if name == page else TEXT)
        self.clear_content()
        titles = {
            "Overview": "Environmental Overview",
            "Weather Explorer": "Weather Explorer",
            "Climate Analytics": "Climate Analytics",
            "Data Lab": "Environmental Data Lab",
            "Alert Center": "Alert Center",
            "Reports": "Reports & Exports",
            "Settings": "Settings",
        }
        self.page_title.configure(text=titles.get(page, page))
        pages = {
            "Overview": self.page_overview,
            "Weather Explorer": self.page_weather,
            "Climate Analytics": self.page_analytics,
            "Data Lab": self.page_data_lab,
            "Alert Center": self.page_alerts,
            "Reports": self.page_reports,
            "Settings": self.page_settings,
        }
        pages.get(page, self.page_settings)()

    # ---------------------------------------------------------------- widgets
    @staticmethod
    def _next_row(parent):
        """Next free grid row in `parent` (all children of self.content use grid)."""
        rows = [int(w.grid_info().get("row", -1)) for w in parent.grid_slaves()]
        return max(rows) + 1 if rows else 0

    def section_label(self, parent, text, subtitle=None):
        # FIX: use grid (not pack) because self.content already uses grid.
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=self._next_row(parent), column=0, sticky="w", pady=(6, 0))
        ctk.CTkLabel(box, text=text, text_color=TEXT,
                     font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", pady=(0, 2))
        if subtitle:
            ctk.CTkLabel(box, text=subtitle, text_color=MUTED,
                         font=ctk.CTkFont(size=11)).pack(anchor="w", pady=(0, 12))
        return box

    def card(self, parent, title, value, detail, accent=ACCENT):
        frame = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=16, border_width=1, border_color="#1C3B2E")
        ctk.CTkFrame(frame, fg_color=accent, height=3, corner_radius=3).pack(fill="x", padx=15, pady=(14, 10))
        ctk.CTkLabel(frame, text=title.upper(), text_color=MUTED,
                     font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w", padx=16)
        ctk.CTkLabel(frame, text=value, text_color=TEXT,
                     font=ctk.CTkFont(size=27, weight="bold")).pack(anchor="w", padx=16, pady=(5, 0))
        ctk.CTkLabel(frame, text=detail, text_color=accent,
                     font=ctk.CTkFont(size=11)).pack(anchor="w", padx=16, pady=(2, 14))
        return frame

    def make_chart(self, parent, title, labels, values, ylabel, chart_type="line"):
        frame = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=16, border_width=1, border_color="#1C3B2E")
        ctk.CTkLabel(frame, text=title, text_color=TEXT,
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=17, pady=(15, 0))
        fig = Figure(figsize=(5.7, 2.55), dpi=100, facecolor=CARD)
        ax = fig.add_subplot(111)
        ax.set_facecolor(CARD)
        xs = list(range(len(values)))
        if chart_type == "bar":
            ax.bar(xs, values, color=ACCENT_2, width=0.55)
        else:
            ax.plot(xs, values, color=ACCENT, linewidth=2.5, marker="o",
                    markersize=5, markerfacecolor=ACCENT_2)
            ax.fill_between(xs, values, min(values) - 2, color=ACCENT, alpha=0.08)
        ax.set_xticks(xs)
        ax.set_xticklabels(labels)
        ax.set_ylabel(ylabel, color=MUTED, fontsize=9)
        ax.tick_params(colors=MUTED, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color("#2A4A3B")
        ax.grid(axis="y", color="#234334", alpha=0.6, linestyle="--")
        fig.tight_layout(pad=1.5)
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=(0, 8))
        return frame

    # --------------------------------------------------------------- overview
    def page_overview(self):
        intro = ctk.CTkFrame(self.content, fg_color="transparent")
        intro.grid(row=0, column=0, sticky="ew", pady=(0, 17))
        intro.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(intro, text="Understand the planet, one signal at a time.",
                     text_color=MUTED, font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(intro, text="↻  Refresh Weather", width=155, height=35,
                      fg_color=ACCENT_2, hover_color="#209E8B", text_color="#06130E",
                      command=self.fetch_weather).grid(row=0, column=1, sticky="e")

        w = self.last_weather
        if w:
            temp_v, temp_d = f"{w['temperature']:.1f}°C", f"Live • {w['city']}"
            hum_v, hum_d = f"{w['humidity']:.0f}%", f"Live • {w['city']}"
            rain_v, rain_d = f"{w['precipitation']:.1f} mm", f"Live • {w['city']}"
        else:
            temp_v, temp_d = "29.4°C*", "Illustrative sample reading"
            hum_v, hum_d = "68%*", "Illustrative sample reading"
            rain_v, rain_d = "4.2 mm*", "Illustrative sample reading"

        metrics = ctk.CTkFrame(self.content, fg_color="transparent")
        metrics.grid(row=1, column=0, sticky="ew", pady=(0, 18))
        for i in range(4):
            metrics.grid_columnconfigure(i, weight=1)
        self.card(metrics, "Temperature", temp_v, temp_d).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.card(metrics, "Relative Humidity", hum_v, hum_d, ACCENT_2).grid(row=0, column=1, sticky="ew", padx=8)
        self.card(metrics, "Precipitation", rain_v, rain_d, SKY).grid(row=0, column=2, sticky="ew", padx=8)
        self.card(metrics, "Air Quality", "Demo", "No air-quality sensor connected", WARNING).grid(
            row=0, column=3, sticky="ew", padx=(8, 0))

        note = ctk.CTkFrame(self.content, fg_color="#172D22", corner_radius=12)
        note.grid(row=2, column=0, sticky="ew", pady=(0, 18))
        ctk.CTkLabel(note, text="ⓘ  Demo data is marked with *. Use Weather Explorer or Refresh Weather to retrieve current weather from Open-Meteo.",
                     text_color="#C7D9CC", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=15, pady=12)

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        charts = ctk.CTkFrame(self.content, fg_color="transparent")
        charts.grid(row=3, column=0, sticky="ew")
        charts.grid_columnconfigure((0, 1), weight=1)
        self.make_chart(charts, "Temperature trend • sample", days,
                        [28, 29, 31, 30, 32, 29, 30], "Temperature (°C)").grid(
            row=0, column=0, sticky="nsew", padx=(0, 8))
        self.make_chart(charts, "Rainfall • sample", days,
                        [2, 5, 0, 8, 3, 1, 4], "Rainfall (mm)", "bar").grid(
            row=0, column=1, sticky="nsew", padx=(8, 0))

        self.section_label(self.content, "Field notes", "A quick, practical summary of what this workspace can do.")
        tips = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=14)
        tips.grid(row=self._next_row(self.content), column=0, sticky="ew", pady=(0, 15))
        for item in [
            "01  Connect to Open-Meteo for current weather conditions.",
            "02  Import CSV datasets to explore measurements from your own sources.",
            "03  Configure simple threshold alerts and export a report for your records.",
        ]:
            ctk.CTkLabel(tips, text=item, text_color=TEXT, anchor="w",
                         font=ctk.CTkFont(size=12)).pack(fill="x", padx=17, pady=8)

    # ---------------------------------------------------------------- weather
    def page_weather(self):
        self.section_label(self.content, "Live weather lookup",
                           "Fetch current conditions from Open-Meteo. Internet access is required.")
        panel = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=16)
        panel.grid(row=self._next_row(self.content), column=0, sticky="ew", pady=(0, 16))
        panel.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(panel, text="City", text_color=MUTED).grid(row=0, column=0, padx=(18, 8), pady=18)
        entry = ctk.CTkEntry(panel, textvariable=self.city_var, height=38, placeholder_text="e.g. Vijayawada")
        entry.grid(row=0, column=1, sticky="ew", padx=8, pady=18)
        entry.bind("<Return>", lambda _e: self.fetch_weather())
        ctk.CTkButton(panel, text="Fetch weather", fg_color=ACCENT, hover_color="#35C983",
                      text_color="#06130E", command=self.fetch_weather).grid(row=0, column=2, padx=18, pady=18)

        self.weather_result = ctk.CTkFrame(self.content, fg_color="transparent")
        self.weather_result.grid(row=self._next_row(self.content), column=0, sticky="ew")
        self.weather_result.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.render_weather_result(self.last_weather)

        ctk.CTkLabel(self.content,
                     text="Weather values come from Open-Meteo's current-weather endpoint and are not air-quality measurements.",
                     text_color=MUTED, wraplength=800, font=ctk.CTkFont(size=11)).grid(
            row=self._next_row(self.content), column=0, sticky="w", pady=12)

    def render_weather_result(self, weather):
        for child in self.weather_result.winfo_children():
            child.destroy()
        if not weather:
            ctk.CTkLabel(self.weather_result,
                         text="No live reading loaded yet. Enter a city and select Fetch weather.",
                         text_color=MUTED, font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w", pady=10)
            return
        desc = WEATHER_CODES.get(weather["code"], f"Code {weather['code']}")
        self.card(self.weather_result, "Temperature", f"{weather['temperature']:.1f}°C",
                  f"Feels like {weather['feels_like']:.1f}°C").grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.card(self.weather_result, "Humidity", f"{weather['humidity']:.0f}%",
                  f"Precipitation {weather['precipitation']:.1f} mm", ACCENT_2).grid(
            row=0, column=1, sticky="ew", padx=8)
        self.card(self.weather_result, "Wind speed", f"{weather['wind']:.1f} km/h",
                  f"Direction {weather.get('wind_direction', '—')}°", WARNING).grid(
            row=0, column=2, sticky="ew", padx=8)
        self.card(self.weather_result, "Condition", desc,
                  f"Observed {weather.get('time', 'now')}", SKY).grid(row=0, column=3, sticky="ew", padx=(8, 0))
        ctk.CTkLabel(self.weather_result,
                     text=f"Location: {weather['city']}  •  Coordinates: {weather['latitude']:.3f}, {weather['longitude']:.3f}",
                     text_color=MUTED, font=ctk.CTkFont(size=11)).grid(
            row=1, column=0, columnspan=4, sticky="w", pady=12)

    def fetch_weather(self):
        city = self.city_var.get().strip()
        if not city:
            messagebox.showwarning("City required", "Enter a city name first.")
            return
        self.status_var.set(f"Looking up {city}…")
        threading.Thread(target=self._weather_worker, args=(city,), daemon=True).start()

    def _weather_worker(self, city):
        try:
            q = urllib.parse.urlencode({"name": city, "count": 1, "language": "en", "format": "json"})
            with urllib.request.urlopen(f"https://geocoding-api.open-meteo.com/v1/search?{q}", timeout=12) as r:
                geo = json.loads(r.read().decode("utf-8"))
            results = geo.get("results") or []
            if not results:
                raise ValueError(f"No location found for '{city}'. Try a nearby major city.")
            loc = results[0]
            params = urllib.parse.urlencode({
                "latitude": loc["latitude"], "longitude": loc["longitude"],
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,"
                           "rain,showers,weather_code,wind_speed_10m,wind_direction_10m",
                "timezone": "auto",
            })
            with urllib.request.urlopen(f"https://api.open-meteo.com/v1/forecast?{params}", timeout=12) as r:
                payload = json.loads(r.read().decode("utf-8"))
            current = payload.get("current", {})
            temperature = float(current.get("temperature_2m", 0))
            weather = {
                "city": loc.get("name", city),
                "latitude": loc["latitude"], "longitude": loc["longitude"],
                "temperature": temperature,
                "feels_like": float(current.get("apparent_temperature", temperature)),
                "humidity": float(current.get("relative_humidity_2m", 0)),
                "wind": float(current.get("wind_speed_10m", 0)),
                "wind_direction": current.get("wind_direction_10m", "—"),
                "precipitation": float(current.get("precipitation", 0)),
                "code": current.get("weather_code", "—"),
                "time": current.get("time", "now"),
            }
            self.after(0, lambda: self._weather_success(weather))
        except Exception as exc:
            self.after(0, lambda err=str(exc): self._weather_error(err))

    def _weather_success(self, weather):
        self.last_weather = weather
        self.city_var.set(weather["city"])
        self.status_var.set(f"Live weather loaded • {weather['city']} • {weather['time']}")
        if self.active_page == "Weather Explorer":
            self.render_weather_result(weather)
        elif self.active_page == "Overview":
            self.show_page("Overview")
        messagebox.showinfo("Weather updated", f"Weather data loaded for {weather['city']}.")

    def _weather_error(self, error):
        self.status_var.set("Weather lookup failed • check internet and city name")
        messagebox.showerror("Weather lookup failed", f"{error}\n\nCheck your internet connection and try again.")

    # -------------------------------------------------------------- analytics
    def page_analytics(self):
        self.section_label(self.content, "Climate analytics",
                           "Illustrative chart values below are demo data, not measured observations.")
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        row = ctk.CTkFrame(self.content, fg_color="transparent")
        row.grid(row=self._next_row(self.content), column=0, sticky="ew", pady=(0, 14))
        row.grid_columnconfigure((0, 1), weight=1)
        self.make_chart(row, "Weekly temperature trend • demo", days,
                        [28, 29, 31, 30, 32, 29, 30], "°C").grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.make_chart(row, "Weekly rainfall • demo", days,
                        [2, 5, 0, 8, 3, 1, 4], "mm", "bar").grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.section_label(self.content, "Analyze your own dataset",
                           "Use Data Lab to import a CSV and inspect its columns and summary statistics.")
        ctk.CTkButton(self.content, text="Open Data Lab →", command=lambda: self.show_page("Data Lab"),
                      fg_color=ACCENT, hover_color="#35C983", text_color="#06130E", height=38).grid(
            row=self._next_row(self.content), column=0, sticky="w")

    # --------------------------------------------------------------- data lab
    def page_data_lab(self):
        self.section_label(self.content, "CSV data workspace",
                           "Import a CSV file to inspect its shape, columns, and numeric summaries.")
        actions = ctk.CTkFrame(self.content, fg_color="transparent")
        actions.grid(row=self._next_row(self.content), column=0, sticky="ew", pady=(0, 12))
        ctk.CTkButton(actions, text="＋ Import CSV", command=self.import_csv, fg_color=ACCENT,
                      hover_color="#35C983", text_color="#06130E", height=38).pack(side="left")
        ctk.CTkButton(actions, text="Load demo dataset", command=self.load_demo_csv,
                      fg_color=CARD_ALT, hover_color="#214737", text_color=TEXT, height=38).pack(side="left", padx=10)
        self.data_info = ctk.CTkLabel(self.content, text="No dataset loaded.", text_color=MUTED, anchor="w")
        self.data_info.grid(row=self._next_row(self.content), column=0, sticky="ew", pady=(0, 10))
        self.data_text = ctk.CTkTextbox(self.content, height=360, fg_color=CARD, text_color=TEXT,
                                        border_color="#1C3B2E", border_width=1, corner_radius=12)
        self.data_text.grid(row=self._next_row(self.content), column=0, sticky="nsew")
        self.data_text.insert(
            "1.0",
            "Your imported dataset preview and summary will appear here.\n\n"
            "Tip: columns such as date, temperature, rainfall, humidity, and location "
            "are useful for environmental datasets.")
        self.data_text.configure(state="disabled")

    def import_csv(self):
        path = filedialog.askopenfilename(title="Choose environmental CSV",
                                          filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            df = pd.read_csv(path)
            self._show_dataframe(df, Path(path).name)
            self.status_var.set(f"Loaded CSV • {Path(path).name}")
        except Exception as exc:
            messagebox.showerror("CSV import failed", str(exc))

    def load_demo_csv(self):
        demo = pd.DataFrame({
            "day": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "temperature_c": [28, 29, 31, 30, 32, 29, 30],
            "rainfall_mm": [2, 5, 0, 8, 3, 1, 4],
            "humidity_percent": [66, 68, 71, 73, 69, 65, 67],
        })
        self._show_dataframe(demo, "built-in demo dataset (illustrative)")
        self.status_var.set("Demo dataset loaded")

    def _show_dataframe(self, df, name):
        self.data_info.configure(text=f"{name}  •  {len(df):,} rows × {len(df.columns):,} columns")
        self.data_text.configure(state="normal")
        self.data_text.delete("1.0", "end")
        self.data_text.insert("end", "PREVIEW (first 12 rows)\n")
        self.data_text.insert("end", df.head(12).to_string(index=False))
        self.data_text.insert("end", "\n\nCOLUMNS\n" + ", ".join(map(str, df.columns)))
        numeric = df.select_dtypes(include="number")
        if not numeric.empty:
            self.data_text.insert("end", "\n\nNUMERIC SUMMARY\n" + numeric.describe().round(2).to_string())
        self.data_text.configure(state="disabled")

    # ----------------------------------------------------------------- alerts
    def page_alerts(self):
        self.section_label(self.content, "Threshold alert center",
                           "These are local rules applied to values you enter; they are not emergency warnings.")
        panel = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=16)
        panel.grid(row=self._next_row(self.content), column=0, sticky="ew", pady=(0, 14))
        panel.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(panel, text="Temperature (°C)", text_color=TEXT).grid(row=0, column=0, padx=16, pady=14, sticky="w")
        temp = ctk.CTkEntry(panel, placeholder_text="e.g. 38")
        temp.grid(row=0, column=1, padx=10, pady=14, sticky="ew")
        ctk.CTkLabel(panel, text="Alert threshold (°C)", text_color=TEXT).grid(row=1, column=0, padx=16, pady=14, sticky="w")
        threshold = ctk.CTkEntry(panel)
        threshold.insert(0, "35")
        threshold.grid(row=1, column=1, padx=10, pady=14, sticky="ew")
        result = ctk.CTkLabel(panel, text="Enter a reading and threshold to evaluate a local rule.",
                              text_color=MUTED, font=ctk.CTkFont(size=12))
        result.grid(row=3, column=0, columnspan=2, sticky="w", padx=16, pady=(5, 18))

        def evaluate():
            try:
                value = float(temp.get())
                limit = float(threshold.get())
            except ValueError:
                messagebox.showwarning("Invalid values", "Enter numeric values in both fields.")
                return
            if value >= limit:
                result.configure(text=f"⚑ THRESHOLD EXCEEDED: {value:.1f}°C is at or above {limit:.1f}°C.",
                                 text_color=WARNING)
            else:
                result.configure(text=f"✓ Within configured threshold: {value:.1f}°C is below {limit:.1f}°C.",
                                 text_color=ACCENT)

        ctk.CTkButton(panel, text="Evaluate rule", command=evaluate, fg_color=ACCENT_2,
                      hover_color="#209E8B", text_color="#06130E").grid(row=2, column=0, padx=16, pady=10, sticky="w")
        info = ctk.CTkFrame(self.content, fg_color="#172D22", corner_radius=12)
        info.grid(row=self._next_row(self.content), column=0, sticky="ew")
        ctk.CTkLabel(info,
                     text="Safety note: TerraPulse is an educational monitoring dashboard. Do not use it as a "
                          "substitute for official weather, flood, health, or emergency alerts.",
                     text_color="#C7D9CC", wraplength=850, justify="left").pack(anchor="w", padx=15, pady=13)

    # ---------------------------------------------------------------- reports
    def page_reports(self):
        self.section_label(self.content, "Export your workspace",
                           "Save a report as a text file or export the most recent live weather reading as JSON.")
        panel = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=16)
        panel.grid(row=self._next_row(self.content), column=0, sticky="ew", pady=(0, 14))
        ctk.CTkLabel(panel, text="Generate a concise TerraPulse status report.",
                     text_color=TEXT).pack(anchor="w", padx=18, pady=(18, 8))
        ctk.CTkButton(panel, text="Export status report (.txt)", command=self.export_report,
                      fg_color=ACCENT, hover_color="#35C983", text_color="#06130E").pack(anchor="w", padx=18, pady=(0, 12))
        ctk.CTkButton(panel, text="Export latest weather (.json)", command=self.export_weather,
                      fg_color=CARD_ALT, hover_color="#214737", text_color=TEXT).pack(anchor="w", padx=18, pady=(0, 18))
        ctk.CTkLabel(self.content, text="Reports distinguish demo values from live weather data.",
                     text_color=MUTED).grid(row=self._next_row(self.content), column=0, sticky="w")

    def export_report(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="terrapulse_report.txt",
                                            filetypes=[("Text files", "*.txt")])
        if not path:
            return
        content = [
            "TERRAPULSE — ENVIRONMENTAL INTELLIGENCE REPORT",
            f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
            "",
            "Data notes:",
            "- Overview and analytics charts use illustrative demo values.",
            "- No air-quality sensor or air-quality API is connected in this version.",
            f"- Last live weather reading: "
            f"{json.dumps(self.last_weather, ensure_ascii=False) if self.last_weather else 'No live reading loaded.'}",
            "",
            "This educational report is not an official warning or forecast.",
        ]
        Path(path).write_text("\n".join(content), encoding="utf-8")
        self.status_var.set(f"Report exported • {Path(path).name}")
        messagebox.showinfo("Export complete", f"Saved report to:\n{path}")

    def export_weather(self):
        if not self.last_weather:
            messagebox.showinfo("No live weather", "Fetch live weather first in Weather Explorer.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", initialfile="terrapulse_weather.json",
                                            filetypes=[("JSON files", "*.json")])
        if not path:
            return
        Path(path).write_text(json.dumps(self.last_weather, indent=2), encoding="utf-8")
        self.status_var.set(f"Weather exported • {Path(path).name}")
        messagebox.showinfo("Export complete", f"Saved weather data to:\n{path}")

    # --------------------------------------------------------------- settings
    def page_settings(self):
        self.section_label(self.content, "Application settings", "A few practical controls for this desktop build.")
        panel = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=16)
        panel.grid(row=self._next_row(self.content), column=0, sticky="ew", pady=(0, 15))
        ctk.CTkLabel(panel, text="Appearance", text_color=TEXT,
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=18, pady=(18, 8))
        ctk.CTkLabel(panel, text="Current theme: Midnight Forest  •  Dark mode",
                     text_color=MUTED).pack(anchor="w", padx=18, pady=(0, 14))
        ctk.CTkLabel(panel, text="Data and privacy", text_color=TEXT,
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=18, pady=(8, 8))
        ctk.CTkLabel(panel, text="CSV files are read locally. Live weather requests send the city lookup to Open-Meteo.",
                     text_color=MUTED, wraplength=760, justify="left").pack(anchor="w", padx=18, pady=(0, 18))
        ctk.CTkButton(self.content, text="Open Reports & Exports →",
                      command=lambda: self.show_page("Reports"), fg_color=ACCENT,
                      hover_color="#35C983", text_color="#06130E").grid(
            row=self._next_row(self.content), column=0, sticky="w")


if __name__ == "__main__":
    app = TerraPulseApp()
    app.mainloop()