import sys
import requests
import os
from datetime import datetime, timedelta
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, Gdk

class NamazVakitleriApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.uygulama.namazvakitleri_turkuaz")
        self.timings = None
        self.hicri_tarih = ""
        self.cards = {}
        self.config_file = os.path.join(os.path.expanduser("~"), ".namaz_sehir.txt")
        self.css_setup()

    def css_setup(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data("""
            window {
                background-color: #008080; 
            }
            .ana-kutu {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 20px;
            }
            .vakit-kart {
                background-color: rgba(255, 255, 255, 0.9);
                border-radius: 12px;
                margin: 4px;
                padding: 10px 20px;
            }
            .aktif-vakit {
                background-color: #e0f7fa;
                border: 3px solid #00ced1;
                box-shadow: 0 0 10px rgba(0,206,209,0.5);
            }
            .vakit-isim { font-size: 18px; color: #004d40; font-weight: 600; }
            .vakit-saat { font-size: 20px; font-weight: bold; color: #000; }
            .ana-sayac { font-size: 58px; font-weight: bold; color: #ffffff; }
            .bilgi-yazisi { font-size: 16px; color: #e0f2f1; font-weight: 800; }
            
            /* Takvim Boyutları Eşitlendi */
            .tarih-etiket, .hicri-etiket { 
                font-size: 15px; 
                font-weight: bold; 
                color: #ffffff; 
            }
            
            .entry-stil { border-radius: 8px; padding: 8px; font-weight: 500; }
            
            /* BUTON GÜNCELLEMESİ: Yazı rengi SİYAH yapıldı */
            .btn-stil { 
                background-color: #004d40; 
                color: #000000; /* Siyah renk */
                border-radius: 8px; 
                font-weight: 900; 
                padding: 6px 12px;
            }
        """.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def do_activate(self):
        self.window = Gtk.ApplicationWindow(application=self, title="Namaz Vakitleri Turkuaz")
        self.window.set_default_size(390, 750)

        overlay_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        overlay_box.add_css_class("ana-kutu")
        overlay_box.set_margin_top(15)
        overlay_box.set_margin_bottom(15)
        overlay_box.set_margin_start(15)
        overlay_box.set_margin_end(15)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        main_box.set_halign(Gtk.Align.CENTER)
        overlay_box.append(main_box)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(overlay_box)
        self.window.set_child(scrolled)

        self.next_prayer_info = Gtk.Label(label="Yükleniyor...")
        self.next_prayer_info.add_css_class("bilgi-yazisi")
        main_box.append(self.next_prayer_info)

        self.countdown_label = Gtk.Label(label="00:00:00")
        self.countdown_label.add_css_class("ana-sayac")
        main_box.append(self.countdown_label)

        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_row.set_halign(Gtk.Align.CENTER)
        main_box.append(input_row)

        self.city_entry = Gtk.Entry(placeholder_text="Şehir...")
        self.city_entry.add_css_class("entry-stil")
        
        fetch_btn = Gtk.Button(label="Sorgula")
        fetch_btn.add_css_class("btn-stil")
        fetch_btn.connect("clicked", lambda x: self.fetch_data())
        
        auto_btn = Gtk.Button(label="📍")
        auto_btn.add_css_class("btn-stil")
        auto_btn.connect("clicked", lambda x: self.auto_locate())

        input_row.append(self.city_entry)
        input_row.append(fetch_btn)
        input_row.append(auto_btn)

        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main_box.append(self.list_box)

        self.date_label = Gtk.Label()
        self.date_label.add_css_class("tarih-etiket")
        main_box.append(self.date_label)

        self.hicri_label = Gtk.Label()
        self.hicri_label.add_css_class("hicri-etiket")
        main_box.append(self.hicri_label)

        self.load_last_city()
        GLib.timeout_add(1000, self.update_timer)
        self.window.present()

    def load_last_city(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                city = f.read().strip()
                if city:
                    self.city_entry.set_text(city)
                    self.fetch_data()
                    return
        self.auto_locate()

    def save_city(self, city):
        with open(self.config_file, "w") as f:
            f.write(city)

    def get_turkish_date(self):
        aylar = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        now = datetime.now()
        return f"{now.day} {aylar[now.month - 1]} {now.year}, {gunler[now.weekday()]}"

    def auto_locate(self):
        try:
            res = requests.get("http://ip-api.com/json/", timeout=5).json()
            if res['status'] == 'success':
                self.city_entry.set_text(res['city'])
                self.fetch_data()
        except:
            self.next_prayer_info.set_text("Konum Hatası!")

    def fetch_data(self):
        city = self.city_entry.get_text()
        if not city: return
        try:
            url = f"http://api.aladhan.com/v1/timingsByCity?city={city}&country=&method=13"
            r = requests.get(url, timeout=5).json()
            if r['code'] == 200:
                self.timings = r['data']['timings']
                h = r['data']['date']['hijri']
                aylar_tr = {"Muharram": "Muharrem", "Safar": "Safer", "Rabi' al-awwal": "Rebiülevvel", "Rabi' al-thani": "Rebiülahir", "Jumada al-ula": "Cemaziyelevvel", "Jumada al-akhira": "Cemaziyelahir", "Rajab": "Recep", "Sha'ban": "Şaban", "Ramadan": "Ramazan", "Shawwal": "Şevval", "Dhu al-Qi'dah": "Zilkade", "Dhu al-Hijjah": "Zilhicce"}
                h_ay = aylar_tr.get(h['month']['en'], h['month']['en'])
                self.hicri_tarih = f"{h['day']} {h_ay} {h['year']}"
                self.date_label.set_text(f"Miladi: {self.get_turkish_date()}")
                self.hicri_label.set_text(f"Hicri: {self.hicri_tarih}")
                self.save_city(city)
                self.update_list_ui()
        except:
            self.next_prayer_info.set_text("Veri alınamadı!")

    def update_list_ui(self):
        child = self.list_box.get_first_child()
        while child:
            self.list_box.remove(child)
            child = self.list_box.get_first_child()

        self.cards = {}
        vakitler = [("Fajr", "İmsak"), ("Sunrise", "Güneş"), ("Dhuhr", "Öğle"), 
                    ("Asr", "İkindi"), ("Maghrib", "Akşam"), ("Isha", "Yatsı")]

        for api_key, tr_name in vakitler:
            card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            card.add_css_class("vakit-kart")
            card.set_size_request(330, 55)
            
            name_lbl = Gtk.Label(label=tr_name, xalign=0, hexpand=True)
            name_lbl.add_css_class("vakit-isim")
            
            time_val = self.timings[api_key].split(" ")[0]
            time_lbl = Gtk.Label(label=time_val)
            time_lbl.add_css_class("vakit-saat")
            
            card.append(name_lbl)
            card.append(time_lbl)
            self.list_box.append(card)
            self.cards[api_key] = card

    def update_timer(self):
        if not self.timings: return True
        now = datetime.now()
        vakit_sirasi = [("Fajr", "İmsak"), ("Sunrise", "Güneş"), ("Dhuhr", "Öğle"), 
                        ("Asr", "İkindi"), ("Maghrib", "Akşam"), ("Isha", "Yatsı")]
        
        target, target_name = None, ""
        current_vakit_key = "Isha"

        for i, (api_key, tr_name) in enumerate(vakit_sirasi):
            t_str = self.timings[api_key].split(" ")[0]
            h, m = map(int, t_str.split(":"))
            p_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
            
            if p_time > now:
                target, target_name = p_time, tr_name
                current_vakit_key = vakit_sirasi[i-1][0] if i > 0 else "Isha"
                break
        
        if not target:
            t_str = self.timings["Fajr"].split(" ")[0]
            h, m = map(int, t_str.split(":"))
            target = now.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(days=1)
            target_name = "İmsak"
            current_vakit_key = "Isha"

        for key, card in self.cards.items():
            if key == current_vakit_key:
                card.add_css_class("aktif-vakit")
            else:
                card.remove_css_class("aktif-vakit")

        diff = target - now
        secs = int(diff.total_seconds())
        self.countdown_label.set_text(f"{secs//3600:02}:{(secs%3600)//60:02}:{secs%60:02}")
        self.next_prayer_info.set_text(f"{target_name} vaktine kalan")
        return True

if __name__ == "__main__":
    app = NamazVakitleriApp()
    app.run(sys.argv)