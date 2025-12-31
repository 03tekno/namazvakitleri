import sys
import requests
import json
import os
import threading
from datetime import datetime, timedelta
import locale
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio, Gdk

try:
    locale.setlocale(locale.LC_ALL, 'tr_TR.UTF-8')
except:
    pass 

SETTINGS_FILE = "settings.json"

class NamazVaktiApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.uygulama.namazvakti",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.load_settings()
        self.vakitler = {}
        self.vakit_anahtarlari = ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"]
        self.vakit_adlari = {
            "Fajr": "İmsak", "Sunrise": "Güneş", "Dhuhr": "Öğle", 
            "Asr": "İkindi", "Maghrib": "Akşam", "Isha": "Yatsı"
        }

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    self.settings = json.load(f)
            except:
                self.settings = {"city": "Istanbul", "notifications": True}
        else:
            self.settings = {"city": "Istanbul", "notifications": True}

    def save_settings(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f)

    def load_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data("""
            .active-vakit { 
                background-color: alpha(@accent_bg_color, 0.2); 
                border-radius: 10px;
                border: 1px solid @accent_bg_color;
            }
            label.clock-label { font-size: 36pt; font-weight: 800; font-variant-numeric: tabular-nums; }
        """.encode())
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def show_about(self, action, param):
        # Hakkında penceresi (Hazırlayan bilgileri)
        about = Adw.AboutWindow(
            transient_for=self.win,
            application_name="Namaz Vakitleri",
            application_icon="com.uygulama.namazvakti", # Varsa ikon adınız
            version="1.0.0",
            developer_name="mobilturka",
            website="https://github.com/03tekno",
            copyright="© 2026",
            license_type=Gtk.License.GPL_3_0
        )
        about.present()

    def do_activate(self):
        self.win = Adw.ApplicationWindow(application=self)
        self.win.set_title("Namaz Vakitleri")
        self.win.set_default_size(400, 750)
        self.load_css()

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_content(main_box)

        # --- ÜST ÇUBUK (HeaderBar) ---
        header = Adw.HeaderBar()
        
        # Hazırlayan Butonu (Hakkında)
        about_btn = Gtk.Button(icon_name="help-about-symbolic")
        about_btn.set_tooltip_text("Hazırlayan / Hakkında")
        about_btn.connect("clicked", lambda x: self.show_about(None, None))
        header.pack_end(about_btn)
        
        main_box.append(header)

        clamp = Adw.Clamp()
        main_box.append(clamp)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        box.set_margin_start(20); box.set_margin_end(20)
        box.set_margin_top(20); box.set_margin_bottom(20)
        clamp.set_child(box)

        # Saat ve Kalan Süre Kartı
        time_card = Adw.PreferencesGroup()
        time_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.time_label = Gtk.Label(); self.time_label.add_css_class("clock-label")
        self.remaining_label = Gtk.Label()
        self.remaining_label.set_markup("<span size='large' foreground='#3584e4'>Yükleniyor...</span>")
        self.date_label = Gtk.Label(); self.date_label.set_opacity(0.7)
        time_vbox.append(self.time_label); time_vbox.append(self.remaining_label); time_vbox.append(self.date_label)
        time_card.add(time_vbox)
        box.append(time_card)

        # Konum Ayarı
        group_city = Adw.PreferencesGroup(title="Konum")
        self.city_entry = Gtk.Entry(text=self.settings["city"])
        self.btn_update = Gtk.Button(label="Güncelle", css_classes=["suggested-action"])
        self.btn_update.connect("clicked", self.on_update_clicked)
        group_city.add(self.city_entry)
        box.append(group_city); box.append(self.btn_update)

        # Vakitler
        self.group_vakitler = Adw.PreferencesGroup(title="Vakitler")
        box.append(self.group_vakitler)
        self.rows = {}
        for key in self.vakit_anahtarlari:
            row = Adw.ActionRow(title=self.vakit_adlari[key])
            self.rows[key] = row
            self.group_vakitler.add(row)

        # Ayarlar
        group_settings = Adw.PreferencesGroup(title="Ayarlar")
        notify_row = Adw.ActionRow(title="Ezan Bildirimi")
        self.notify_switch = Gtk.Switch(active=self.settings["notifications"], valign=Gtk.Align.CENTER)
        self.notify_switch.connect("state-set", self.on_notify_toggled)
        notify_row.add_suffix(self.notify_switch)
        group_settings.add(notify_row)
        box.append(group_settings)

        self.win.present()
        self.update_clock()
        self.on_update_clicked(None)
        
        GLib.timeout_add(1000, self.update_clock)
        GLib.timeout_add_seconds(60, self.check_prayer_time)

    # ... (Diğer metodlar: update_clock, on_update_clicked, fetch_vakitler aynı kalacak) ...
    def update_clock(self):
        now = datetime.now()
        self.time_label.set_text(now.strftime("%H:%M:%S"))
        self.date_label.set_text(now.strftime("%d %B %Y, %A"))
        if self.vakitler: self.update_remaining_time(now)
        return True

    def update_remaining_time(self, now):
        next_vakit_key = None; next_vakit_dt = None
        for key in self.vakit_anahtarlari:
            v_time = datetime.strptime(self.vakitler[key], "%H:%M").replace(year=now.year, month=now.month, day=now.day)
            self.rows[key].remove_css_class("active-vakit")
            if now < v_time and next_vakit_key is None:
                next_vakit_key = key; next_vakit_dt = v_time
        if next_vakit_key is None:
            next_vakit_key = "Fajr"
            next_vakit_dt = datetime.strptime(self.vakitler["Fajr"], "%H:%M").replace(year=now.year, month=now.month, day=now.day) + timedelta(days=1)
            self.rows["Isha"].add_css_class("active-vakit")
        else:
            idx = self.vakit_anahtarlari.index(next_vakit_key)
            self.rows[self.vakit_anahtarlari[idx-1 if idx > 0 else 5]].add_css_class("active-vakit")
        diff = next_vakit_dt - now
        h, rem = divmod(int(diff.total_seconds()), 3600); m, _ = divmod(rem, 60)
        self.remaining_label.set_markup(f"<span foreground='#3584e4'><b>{self.vakit_adlari[next_vakit_key]}</b> vaktine <b>{h}s {m}dk</b> kaldı</span>")

    def on_update_clicked(self, btn):
        city = self.city_entry.get_text()
        self.settings["city"] = city
        self.save_settings()
        if btn: btn.set_sensitive(False)
        threading.Thread(target=lambda: self.post_update(self.fetch_vakitler(city), btn), daemon=True).start()

    def fetch_vakitler(self, city):
        try:
            r = requests.get(f"https://api.aladhan.com/v1/timingsByCity?city={city}&country=Turkey&method=13", timeout=10)
            return r.json()['data']['timings']
        except: return None

    def post_update(self, data, btn):
        def update_ui():
            if btn: btn.set_sensitive(True)
            if data:
                self.vakitler = data
                for key, row in self.rows.items(): row.set_subtitle(data[key])
        GLib.idle_add(update_ui)

    def on_notify_toggled(self, sw, state):
        self.settings["notifications"] = state
        self.save_settings()

    def check_prayer_time(self):
        if self.settings["notifications"] and self.vakitler:
            simdi = datetime.now().strftime("%H:%M")
            for k, v in self.vakit_adlari.items():
                if self.vakitler.get(k) == simdi:
                    n = Gio.Notification.new("Ezan Vakti"); n.set_body(f"{v} vakti girdi.")
                    self.send_notification("ezan", n)
        return True

if __name__ == "__main__":
    app = NamazVaktiApp()
    app.run(sys.argv)
