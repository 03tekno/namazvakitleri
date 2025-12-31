import sys
import requests
from datetime import datetime, timedelta
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, Pango, Gdk

class NamazVakitleriApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.uygulama.namazvakitleri_orta")
        self.timings = None
        self.hicri_tarih = ""
        self.css_setup()

    def css_setup(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data("""
            .vakit-kart {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
                margin: 4px;
                padding: 10px 20px;
            }
            .vakit-isim { font-size: 19px; color: #333; }
            .vakit-saat { font-size: 21px; font-weight: bold; color: #000; }
            .ana-sayac { font-size: 55px; font-weight: bold; color: #000; margin-top: -5px; }
            .bilgi-yazisi { font-size: 17px; color: #666; font-weight: 500; }
            .tarih-etiket { font-size: 15px; font-weight: bold; color: #222; }
            .hicri-etiket { font-size: 14px; color: #666; }
            .oto-btn { background-color: #f0f0f0; border-radius: 8px; font-size: 14px; padding: 5px 10px; }
            .entry-stil { font-size: 14px; padding: 5px; }
        """.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def do_activate(self):
        self.window = Gtk.ApplicationWindow(application=self, title="Namaz Vakitleri")
        self.window.set_default_size(385, 720)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_top(25)
        main_box.set_margin_bottom(25)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        main_box.set_halign(Gtk.Align.CENTER)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(main_box)
        self.window.set_child(scrolled)

        # 1. BİLGİ YAZISI (ÜSTE TAŞINDI)
        self.next_prayer_info = Gtk.Label(label="Yükleniyor...")
        self.next_prayer_info.add_css_class("bilgi-yazisi")
        main_box.append(self.next_prayer_info)

        # 2. SAYAÇ
        self.countdown_label = Gtk.Label(label="00:00:00")
        self.countdown_label.add_css_class("ana-sayac")
        main_box.append(self.countdown_label)

        # 3. GİRİŞ ALANLARI
        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_row.set_halign(Gtk.Align.CENTER)
        main_box.append(input_row)

        self.city_entry = Gtk.Entry(placeholder_text="Şehir")
        self.city_entry.set_width_chars(10)
        self.city_entry.add_css_class("entry-stil")
        
        fetch_btn = Gtk.Button(label="Sorgula")
        fetch_btn.connect("clicked", lambda x: self.fetch_data())
        
        auto_btn = Gtk.Button(label="📍 Konum")
        auto_btn.add_css_class("oto-btn")
        auto_btn.connect("clicked", lambda x: self.auto_locate())

        input_row.append(self.city_entry)
        input_row.append(fetch_btn)
        input_row.append(auto_btn)

        # 4. VAKİT LİSTESİ
        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main_box.append(self.list_box)

        # 5. TARİHLER
        self.date_label = Gtk.Label()
        self.date_label.set_margin_top(20)
        self.date_label.add_css_class("tarih-etiket")
        main_box.append(self.date_label)

        self.hicri_label = Gtk.Label()
        self.hicri_label.add_css_class("hicri-etiket")
        main_box.append(self.hicri_label)

        GLib.idle_add(self.auto_locate)
        GLib.timeout_add(1000, self.update_timer)
        
        self.window.present()

    def get_turkish_date(self):
        aylar = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        now = datetime.now()
        return f"{now.day} {aylar[now.month - 1]} {now.year}, {gunler[now.weekday()]}"

    def get_hicri_ay_tr(self, en_month):
        aylar_tr = {
            "Muharram": "Muharrem", "Safar": "Safer", "Rabi' al-awwal": "Rebiülevvel",
            "Rabi' al-thani": "Rebiülahir", "Jumada al-ula": "Cemaziyelevvel",
            "Jumada al-akhira": "Cemaziyelahir", "Rajab": "Recep", "Sha'ban": "Şaban",
            "Ramadan": "Ramazan", "Shawwal": "Şevval", "Dhu al-Qi'dah": "Zilkade", "Dhu al-Hijjah": "Zilhicce"
        }
        return aylar_tr.get(en_month, en_month)

    def auto_locate(self):
        try:
            res = requests.get("http://ip-api.com/json/").json()
            if res['status'] == 'success':
                self.city_entry.set_text(res['city'])
                self.fetch_data()
        except:
            self.next_prayer_info.set_text("Konum hatası.")

    def fetch_data(self):
        city = self.city_entry.get_text()
        try:
            url = f"http://api.aladhan.com/v1/timingsByCity?city={city}&country=&method=13"
            r = requests.get(url).json()
            if r['code'] == 200:
                self.timings = r['data']['timings']
                h = r['data']['date']['hijri']
                self.hicri_tarih = f"{h['day']} {self.get_hicri_ay_tr(h['month']['en'])} {h['year']}"
                self.date_label.set_text(f"Miladi: {self.get_turkish_date()}")
                self.hicri_label.set_text(f"Hicri: {self.hicri_tarih}")
                self.update_list_ui()
        except:
            self.next_prayer_info.set_text("Veri hatası.")

    def update_list_ui(self):
        child = self.list_box.get_first_child()
        while child:
            self.list_box.remove(child)
            child = self.list_box.get_first_child()

        vakitler = [("Fajr", "İmsak"), ("Sunrise", "Güneş"), ("Dhuhr", "Öğle"), 
                    ("Asr", "İkindi"), ("Maghrib", "Akşam"), ("Isha", "Yatsı")]

        for api_key, tr_name in vakitler:
            card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            card.add_css_class("vakit-kart")
            card.set_size_request(320, 55)
            
            name_lbl = Gtk.Label(label=tr_name, xalign=0, hexpand=True)
            name_lbl.add_css_class("vakit-isim")
            
            time_val = self.timings[api_key].split(" ")[0]
            time_lbl = Gtk.Label(label=time_val)
            time_lbl.add_css_class("vakit-saat")
            
            card.append(name_lbl)
            card.append(time_lbl)
            self.list_box.append(card)

    def update_timer(self):
        if not self.timings: return True
        now = datetime.now()
        vakit_sirasi = [("Fajr", "İmsak"), ("Sunrise", "Güneş"), ("Dhuhr", "Öğle"), 
                        ("Asr", "İkindi"), ("Maghrib", "Akşam"), ("Isha", "Yatsı")]
        
        target = None
        target_name = ""
        for api_key, tr_name in vakit_sirasi:
            t_str = self.timings[api_key].split(" ")[0]
            h, m = map(int, t_str.split(":"))
            p_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if p_time > now:
                target, target_name = p_time, tr_name
                break
        
        if not target:
            t_str = self.timings["Fajr"].split(" ")[0]
            h, m = map(int, t_str.split(":"))
            target = now.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(days=1)
            target_name = "İmsak (Yarın)"

        diff = target - now
        secs = int(diff.total_seconds())
        self.countdown_label.set_text(f"{secs//3600:02}:{(secs%3600)//60:02}:{secs%60:02}")
        self.next_prayer_info.set_text(f"{target_name} vaktine kalan")
        return True

if __name__ == "__main__":
    app = NamazVakitleriApp()
    app.run(sys.argv)