import base64
import json
import os
import re
import threading
import urllib.parse
import urllib.request
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.textinput import TextInput

# ==============================================================================
# KOD BIT AYARLARI
# ==============================================================================
ASISTAN_ADI = "Kod Bit"
NPOINT_BIN_ID = "79a7f7f342542aa9d958"
YEREL_JSON_DOSYASI = "kod_bit_hafiza.json"

GIZLI_ANAHTAR = b"KodBit_Key_Gizli_2026!"
GROQ_MODEL = ""
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"

Window.clearcolor = (0.05, 0.07, 0.11, 1)
Window.minimum_width = 520
Window.minimum_height = 600


def sifreli_key_coz(sifreli_metin: str, anahtar: bytes) -> str:
    temiz = (sifreli_metin or "").strip()
    if not temiz:
        return ""
    try:
        ham = base64.b64decode(temiz.encode("ascii"))
        cozulmus = bytearray()
        for i, b in enumerate(ham):
            k = anahtar[i % len(anahtar)]
            cozulmus.append(b ^ k ^ ((i * 13) & 0xFF))
        return cozulmus.decode("utf-8").strip()
    except Exception:
        return ""


class KodBitHafiza:
    """Bilgileri yerel JSON ve npoint.io bulut JSON uzerinde senkron tutar."""

    def __init__(self, json_dosyasi, bin_id):
        self.json_dosyasi = json_dosyasi
        self.bin_id = bin_id.strip()
        self.npoint_url = (
            f"https://api.npoint.io/{self.bin_id}" if self.bin_id else None
        )
        self.veri = self._yerel_yukle()

    def _varsayilan_veri(self):
        return {
            "kimlik": {
                "ad": ASISTAN_ADI,
                "yaratici": None,
            },
            "kurallar": [],
            "ogrenilenler": [],
        }

    def _yerel_yukle(self):
        if os.path.exists(self.json_dosyasi):
            try:
                with open(self.json_dosyasi, "r", encoding="utf-8") as f:
                    ham = json.load(f)
                if isinstance(ham, dict):
                    kimlik = ham.get("kimlik", {})
                    if not isinstance(kimlik, dict):
                        kimlik = {}
                    kimlik.setdefault("ad", ASISTAN_ADI)
                    kimlik.setdefault("yaratici", None)

                    kurallar = ham.get("kurallar", [])
                    if not isinstance(kurallar, list):
                        kurallar = []

                    ogrenilenler = ham.get("ogrenilenler", [])
                    if not isinstance(ogrenilenler, list):
                        ogrenilenler = []

                    return {
                        "kimlik": kimlik,
                        "kurallar": kurallar,
                        "ogrenilenler": ogrenilenler,
                    }
            except Exception:
                pass
        return self._varsayilan_veri()

    def yerel_kaydet(self):
        with open(self.json_dosyasi, "w", encoding="utf-8") as f:
            json.dump(self.veri, f, ensure_ascii=False, indent=4)

    def _birlestir(self, uzak_veri):
        if not isinstance(uzak_veri, dict):
            return

        uzak_kimlik = uzak_veri.get("kimlik")
        if isinstance(uzak_kimlik, dict):
            if uzak_kimlik.get("ad"):
                self.veri["kimlik"]["ad"] = uzak_kimlik["ad"]
            if uzak_kimlik.get("yaratici"):
                self.veri["kimlik"]["yaratici"] = uzak_kimlik["yaratici"]

        mevcut_kurallar = {str(k).strip().lower() for k in self.veri["kurallar"]}
        for kural in uzak_veri.get("kurallar", []):
            k_str = str(kural).strip()
            if k_str and k_str.lower() not in mevcut_kurallar:
                self.veri["kurallar"].append(k_str)
                mevcut_kurallar.add(k_str.lower())

        mevcut_anahtarlar = {
            (
                str(item.get("soru", "")).strip().lower(),
                str(item.get("cevap", "")).strip().lower(),
            )
            for item in self.veri["ogrenilenler"]
            if isinstance(item, dict)
        }
        for item in uzak_veri.get("ogrenilenler", []):
            if isinstance(item, dict):
                s = str(item.get("soru", "")).strip()
                c = str(item.get("cevap", "")).strip()
                if s and c:
                    anahtar = (s.lower(), c.lower())
                    if anahtar not in mevcut_anahtarlar:
                        self.veri["ogrenilenler"].append({"soru": s, "cevap": c})
                        mevcut_anahtarlar.add(anahtar)

    def npoint_cek(self):
        if not self.npoint_url:
            return "Yerel JSON modu aktif."

        istek = urllib.request.Request(
            self.npoint_url,
            headers={"Accept": "application/json", "User-Agent": "KodBit/1.0"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(istek, timeout=10) as yanit:
                uzak_json = json.loads(yanit.read().decode("utf-8"))
                self._birlestir(uzak_json)
                self.yerel_kaydet()
                return (
                    f"npoint.io senkronize edildi "
                    f"({len(self.veri['kurallar'])} kural, {len(self.veri['ogrenilenler'])} kayit)."
                )
        except Exception as e:
            return f"npoint.io okunamadi, yerel JSON kullaniliyor ({e})."

    def npoint_gonder(self):
        if not self.npoint_url:
            return "Yerel JSON kaydedildi."

        govde = json.dumps(self.veri, ensure_ascii=False).encode("utf-8")
        istek = urllib.request.Request(
            self.npoint_url,
            data=govde,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "KodBit/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(istek, timeout=10):
                return "Yerel JSON + npoint.io guncellendi."
        except Exception as e:
            return f"Yerel JSON kaydedildi; npoint.io yazma hatasi: {e}"

    def ogret(self, metin):
        temiz = metin.strip()
        if not temiz:
            return "Bos bir bilgi ogretemem."

        kucuk = temiz.lower()

        yapimci_eslesme = re.search(
            r"(?:beni yapan|yapimcim|yaratıcim|yaratıcım|beni egiten|beni eğiten|seni yapan|seni gelistiren|seni geliştiren|seni egiten|seni eğiten)\s+(?:kisi\s+|kişi\s+)?(.+)",
            kucuk,
        )
        if yapimci_eslesme:
            deger = yapimci_eslesme.group(1).strip(" .!")
            self.veri["kimlik"]["yaratici"] = deger
            self.yerel_kaydet()
            durum = self.npoint_gonder()
            return f"Tamamdir, beni yapan kisiyi '{deger}' olarak ogrendim. ({durum})"

        for ayrac in ("->", "="):
            if ayrac in temiz:
                soru_kismi, cevap_kismi = temiz.split(ayrac, 1)
                soru_kismi = soru_kismi.strip()
                cevap_kismi = cevap_kismi.strip()
                if soru_kismi and cevap_kismi:
                    self.veri["ogrenilenler"].append(
                        {"soru": soru_kismi, "cevap": cevap_kismi}
                    )
                    self.yerel_kaydet()
                    durum = self.npoint_gonder()
                    return f"Ogrendim: '{soru_kismi}' -> '{cevap_kismi}'. ({durum})"

        if temiz not in self.veri["kurallar"]:
            self.veri["kurallar"].append(temiz)
        self.yerel_kaydet()
        durum = self.npoint_gonder()
        return f"Hafizaya eklendi: '{temiz}'. ({durum})"

    def hafiza_talimati_olustur(self):
        ad = self.veri["kimlik"].get("ad") or ASISTAN_ADI
        yaratici = self.veri["kimlik"].get("yaratici") or "henuz belirtilmedi"

        kurallar_metni = (
            "\n".join([f"- {k}" for k in self.veri["kurallar"]])
            if self.veri["kurallar"]
            else "- Henuz ek kural yok."
        )
        ogrenilen_metni = (
            "\n".join(
                [
                    f"- Soru/Konu: {item.get('soru')} | Ogretilen Yanit/Bilgi: {item.get('cevap')}"
                    for item in self.veri["ogrenilenler"]
                ]
            )
            if self.veri["ogrenilenler"]
            else "- Henuz ogrenilmis kayit yok."
        )

        return (
            f"Senin adin {ad}. Seni yapan / olusturan kisi: {yaratici}.\n"
            "ONEMLI: Kullanicinin sana ogrettigi asagidaki hafiza verilerine ve kurallarina sadik kal. "
            "Sana 'Seni kim yapti?' gibi sorular sorulursa hafizadaki yapimci bilgisini esas al. "
            "Ogretilen kurallar veya eslesmelerle celisen sabit kalip cevaplar verme; kullanicinin istedigi sekilde ve dogal Turkce ile yanitla.\n\n"
            "=== HAFIZADAKI KURALLAR VE IStekLER ===\n"
            f"{kurallar_metni}\n\n"
            "=== HAFIZADAKI OGRENILMIS BILGILER ===\n"
            f"{ogrenilen_metni}"
        )

    def kimlik_ve_ogrenilen_yanit(self, soru):
        s_temiz = re.sub(r"\s+", " ", soru.strip().lower())
        ad = self.veri["kimlik"].get("ad") or ASISTAN_ADI
        yaratici = self.veri["kimlik"].get("yaratici")

        kim_yapti_kaliplari = [
            "seni kim yapti",
            "seni kim yaptı",
            "kim yapti",
            "kim yaptı",
            "yapimcin kim",
            "yapımcın kim",
            "yaraticin kim",
            "yaratıcın kim",
            "seni kim gelistirdi",
            "seni kim geliştirdi",
        ]
        if any(k in s_temiz for k in kim_yapti_kaliplari) and yaratici:
            return f"Beni {yaratici} yapti."

        if any(k in s_temiz for k in ["adin ne", "adın ne", "senin adin", "senin adın", "ismin ne"]):
            return f"Benim adim {ad}."

        s_kelimeler = set(re.findall(r"\w+", s_temiz))
        if not s_kelimeler:
            return None

        for kayit in reversed(self.veri["ogrenilenler"]):
            k_soru = re.sub(r"\s+", " ", str(kayit.get("soru", "")).strip().lower())
            k_cevap = str(kayit.get("cevap", "")).strip()
            if not k_soru or not k_cevap:
                continue
            if k_soru == s_temiz:
                return k_cevap
            k_kelimeler = set(re.findall(r"\w+", k_soru))
            if k_kelimeler and k_kelimeler == s_kelimeler:
                return k_cevap

        return None


class GroqMotoru:
    """Groq API uzerinden aktif modeli bulur ve hafizadaki bilgilere gore yanit uretir."""

    def __init__(self, api_key=""):
        self.api_key = (api_key or "").strip()
        self.secili_model = GROQ_MODEL.strip() if GROQ_MODEL else None
        self.denenen_modeller = set()

    def api_key_ayarla(self, yeni_key: str):
        self.api_key = (yeni_key or "").strip()
        self.denenen_modeller.clear()

    def aktif_mi(self):
        return bool(self.api_key)

    def _model_bul(self):
        if self.secili_model and self.secili_model not in self.denenen_modeller:
            return self.secili_model

        istek = urllib.request.Request(
            GROQ_MODELS_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "KodBit/1.0",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(istek, timeout=10) as yanit:
                veri = json.loads(yanit.read().decode("utf-8"))
                modeller = [
                    m.get("id")
                    for m in veri.get("data", [])
                    if isinstance(m, dict)
                    and m.get("id")
                    and m.get("id") not in self.denenen_modeller
                    and "whisper" not in m.get("id", "").lower()
                    and "guard" not in m.get("id", "").lower()
                ]
                tercih_sirasi = [
                    "llama-3.3-70b-versatile",
                    "llama-3.1-8b-instant",
                    "gemma2-9b-it",
                ]
                for tercih in tercih_sirasi:
                    if tercih in modeller:
                        self.secili_model = tercih
                        return tercih
                if modeller:
                    self.secili_model = modeller[0]
                    return modeller[0]
        except Exception:
            pass
        return "llama-3.1-8b-instant"

    def yanitla(self, soru, hafiza_talimati, gecmis):
        if not self.aktif_mi():
            return None, None

        for _ in range(2):
            model_adi = self._model_bul()
            mesajlar = [{"role": "system", "content": hafiza_talimati}]
            for rol, metin in gecmis[-8:]:
                mesajlar.append({"role": rol, "content": metin})
            mesajlar.append({"role": "user", "content": soru})

            govde = json.dumps(
                {
                    "model": model_adi,
                    "messages": mesajlar,
                    "temperature": 0.7,
                },
                ensure_ascii=False,
            ).encode("utf-8")

            istek = urllib.request.Request(
                GROQ_CHAT_URL,
                data=govde,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "User-Agent": "KodBit/1.0",
                },
                method="POST",
            )

            try:
                with urllib.request.urlopen(istek, timeout=20) as yanit:
                    veri = json.loads(yanit.read().decode("utf-8"))
                    secimler = veri.get("choices", [])
                    if secimler:
                        icerik = (
                            secimler[0].get("message", {}).get("content", "").strip()
                        )
                        if icerik:
                            return icerik, None
            except Exception as e:
                self.denenen_modeller.add(model_adi)
                self.secili_model = None
                if "400" not in str(e) and "404" not in str(e):
                    return None, str(e)

        return None, "Model istegi reddedildi"


class AcikKaynakArama:
    """Groq yanit veremediginde Wikipedia ve DuckDuckGo uzerinden ozet ceker."""

    @staticmethod
    def _wikipedia_ozet(sorgu, dil="tr"):
        encoded = urllib.parse.quote(sorgu.strip())
        url = f"https://{dil}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        istek = urllib.request.Request(url, headers={"User-Agent": "KodBit/1.0"})
        try:
            with urllib.request.urlopen(istek, timeout=8) as yanit:
                veri = json.loads(yanit.read().decode("utf-8"))
                if veri.get("type") == "disambiguation":
                    return None
                ozet = veri.get("extract", "").strip()
                if (
                    not ozet
                    or "şu anlamlara gelebilir" in ozet.lower()
                    or "sunlari ifade edebilir" in ozet.lower()
                ):
                    return None
                cumleler = re.split(r"(?<=[.!?])\s+", ozet)
                return " ".join(cumleler[:2]).strip()
        except Exception:
            pass
        return None

    @staticmethod
    def _duckduckgo_ozet(sorgu):
        encoded = urllib.parse.quote(sorgu.strip())
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        istek = urllib.request.Request(url, headers={"User-Agent": "KodBit/1.0"})
        try:
            with urllib.request.urlopen(istek, timeout=8) as yanit:
                veri = json.loads(yanit.read().decode("utf-8"))
                abstract = veri.get("AbstractText", "").strip()
                if abstract:
                    cumleler = re.split(r"(?<=[.!?])\s+", abstract)
                    return " ".join(cumleler[:2]).strip()
        except Exception:
            pass
        return None

    def yanit_olustur(self, mesaj, asistan_adi="Kod Bit", hata_notu=None):
        metin = mesaj.strip()
        kucuk = metin.lower()

        sohbet = {
            "selam": f"Selam, ben {asistan_adi}. Ne yapalim?",
            "merhaba": f"Merhaba, ben {asistan_adi}.",
            "slm": f"Selam, ben {asistan_adi}.",
            "sus": "Tamam, sustum.",
            "tamam": "Anlasildi.",
        }
        if kucuk in sohbet:
            return sohbet[kucuk]

        konu = re.sub(
            r"\b(nedir|ne demek|kimdir|kim|hakkinda|hakkında|bilgi ver|anlat|bana|selam)\b",
            " ",
            kucuk,
        )
        konu = re.sub(r"\s+", " ", konu).strip(" ?!.,")
        if len(konu) < 2:
            if hata_notu:
                return f"Selam! Groq API hatasi ({hata_notu}) aldim ama seni dinliyorum."
            return f"'{metin}' icin net bir istek goremedim. Ogret kutusundan bana kural/istek ogretebilirsin."

        bilgi = (
            self._wikipedia_ozet(konu, "tr")
            or self._wikipedia_ozet(konu, "en")
            or self._duckduckgo_ozet(konu)
        )
        if bilgi:
            return bilgi

        if hata_notu:
            return f"Groq API hatasi ({hata_notu}) nedeniyle API yaniti alinamadi; '{metin}' icin kayitli eslesme bulunamadi."
        return f"'{metin}' hakkinda hafizada eslesme veya net bir internet ozeti bulamadim."


class MesajKarti(BoxLayout):

    def __init__(self, gonderen, icerik, vurgu_rengi, kart_rengi, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint_y=None,
            padding=[12, 10],
            spacing=4,
            **kwargs,
        )

        with self.canvas.before:
            Color(*kart_rengi)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._guncelle_rect, size=self._guncelle_rect)

        baslik = Label(
            text=f"[b]{gonderen}[/b]",
            markup=True,
            size_hint_y=None,
            height=20,
            halign="left",
            valign="middle",
            color=vurgu_rengi,
        )
        baslik.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))

        govde = Label(
            text=icerik,
            size_hint_y=None,
            halign="left",
            valign="top",
            color=(0.94, 0.96, 0.99, 1),
        )
        govde.bind(
            width=lambda inst, val: setattr(inst, "text_size", (max(val - 4, 50), None))
        )
        govde.bind(
            texture_size=lambda inst, val: setattr(inst, "height", val[1] + 4)
        )

        self.add_widget(baslik)
        self.add_widget(govde)

        govde.bind(
            height=lambda inst, val: setattr(self, "height", val + baslik.height + 24)
        )
        self.height = 54

    def _guncelle_rect(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size


class KodBitArayuz(BoxLayout):

    def __init__(self, groq_motoru, **kwargs):
        super().__init__(orientation="vertical", padding=14, spacing=10, **kwargs)
        self.hafiza = KodBitHafiza(YEREL_JSON_DOSYASI, NPOINT_BIN_ID)
        self.groq = groq_motoru
        self.arama = AcikKaynakArama()
        self.gecmis = []
        self._senkron_basladi = False

        ust_bilgi = BoxLayout(size_hint_y=None, height=36, spacing=10)
        baslik_lbl = Label(
            text=f"[b]{ASISTAN_ADI}[/b]",
            markup=True,
            size_hint_x=0.35,
            halign="left",
            valign="middle",
            color=(0.25, 0.92, 0.78, 1),
            font_size="20sp",
        )
        baslik_lbl.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))

        self.durum_lbl = Label(
            text="Hafiza hazirlaniyor...",
            size_hint_x=0.65,
            halign="right",
            valign="middle",
            color=(0.65, 0.72, 0.82, 1),
            font_size="12sp",
        )
        self.durum_lbl.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))

        ust_bilgi.add_widget(baslik_lbl)
        ust_bilgi.add_widget(self.durum_lbl)
        self.add_widget(ust_bilgi)

        ogret_panel = BoxLayout(size_hint_y=None, height=44, spacing=8)
        self.ogret_input = TextInput(
            hint_text="Ogret: kural/istek yaz veya 'soru -> cevap' gir",
            multiline=False,
            background_color=(0.11, 0.14, 0.20, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.25, 0.92, 0.78, 1),
            padding=[10, 12],
        )
        self.ogret_input.bind(on_text_validate=self.ogret_olayi)

        ogret_btn = Button(
            text="OGRET",
            size_hint_x=0.22,
            background_normal="",
            background_color=(0.05, 0.62, 0.48, 1),
            color=(1, 1, 1, 1),
            bold=True,
        )
        ogret_btn.bind(on_press=self.ogret_olayi)

        ogret_panel.add_widget(self.ogret_input)
        ogret_panel.add_widget(ogret_btn)
        self.add_widget(ogret_panel)

        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.sohbet_listesi = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=8, padding=[2, 2]
        )
        self.sohbet_listesi.bind(minimum_height=self.sohbet_listesi.setter("height"))
        self.scroll.add_widget(self.sohbet_listesi)
        self.add_widget(self.scroll)

        sor_panel = BoxLayout(size_hint_y=None, height=48, spacing=8)
        self.sor_input = TextInput(
            hint_text="Kod Bit'e yaz...",
            multiline=False,
            background_color=(0.11, 0.14, 0.20, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.25, 0.92, 0.78, 1),
            padding=[10, 14],
        )
        self.sor_input.bind(on_text_validate=self.sor_olayi)

        sor_btn = Button(
            text="SOR",
            size_hint_x=0.22,
            background_normal="",
            background_color=(0.16, 0.48, 0.92, 1),
            color=(1, 1, 1, 1),
            bold=True,
        )
        sor_btn.bind(on_press=self.sor_olayi)

        sor_panel.add_widget(self.sor_input)
        sor_panel.add_widget(sor_btn)
        self.add_widget(sor_panel)

        self.kart_ekle(
            ASISTAN_ADI,
            "Hazirim. Ogrettiklerini hafizada tutarim ve Groq aktifse ona gore cevaplarim.",
            (0.25, 0.92, 0.78, 1),
            (0.09, 0.13, 0.19, 1),
        )

    def baslat_senkron(self):
        if not self._senkron_basladi:
            self._senkron_basladi = True
            threading.Thread(target=self._acilis_senkron, daemon=True).start()

    def _acilis_senkron(self):
        durum = self.hafiza.npoint_cek()
        Clock.schedule_once(lambda dt: setattr(self.durum_lbl, "text", durum))

    def kart_ekle(self, gonderen, icerik, vurgu_rengi, kart_rengi):
        kart = MesajKarti(gonderen, icerik, vurgu_rengi, kart_rengi)
        self.sohbet_listesi.add_widget(kart)
        Clock.schedule_once(lambda dt: setattr(self.scroll, "scroll_y", 0), 0.05)

    def ogret_olayi(self, instance):
        metin = self.ogret_input.text.strip()
        if not metin:
            return
        self.ogret_input.text = ""
        threading.Thread(target=self._ogret_islem, args=(metin,), daemon=True).start()

    def _ogret_islem(self, metin):
        sonuc = self.hafiza.ogret(metin)
        Clock.schedule_once(
            lambda dt: (
                setattr(self.durum_lbl, "text", sonuc),
                self.kart_ekle(
                    "HAFIZA",
                    sonuc,
                    (1.0, 0.80, 0.25, 1),
                    (0.16, 0.14, 0.09, 1),
                ),
            )
        )

    def sor_olayi(self, instance):
        soru = self.sor_input.text.strip()
        if not soru:
            return
        self.sor_input.text = ""
        self.kart_ekle(
            "SEN",
            soru,
            (0.55, 0.78, 1.0, 1),
            (0.11, 0.15, 0.23, 1),
        )
        threading.Thread(target=self._sor_islem, args=(soru,), daemon=True).start()

    def _sor_islem(self, soru):
        ad = self.hafiza.veri["kimlik"].get("ad") or ASISTAN_ADI
        yanit = None
        hata_notu = None

        if self.groq.aktif_mi():
            yanit, hata_notu = self.groq.yanitla(
                soru, self.hafiza.hafiza_talimati_olustur(), self.gecmis
            )

        if not yanit:
            yanit = self.hafiza.kimlik_ve_ogrenilen_yanit(soru)
        if not yanit:
            yanit = self.arama.yanit_olustur(soru, asistan_adi=ad, hata_notu=hata_notu)

        self.gecmis.append(("user", soru))
        self.gecmis.append(("assistant", yanit))

        Clock.schedule_once(
            lambda dt: self.kart_ekle(
                ad,
                yanit,
                (0.25, 0.92, 0.78, 1),
                (0.09, 0.13, 0.19, 1),
            )
        )


class AcilisKeyEkrani(Screen):

    def __init__(self, groq_motoru, on_tamam, **kwargs):
        super().__init__(**kwargs)
        self.groq_motoru = groq_motoru
        self.on_tamam = on_tamam

        kutu = BoxLayout(orientation="vertical", padding=24, spacing=14)

        baslik = Label(
            text="[b]Kod Bit — Şifreli API Key Girişi[/b]",
            markup=True,
            size_hint_y=None,
            height=40,
            color=(0.25, 0.92, 0.78, 1),
            font_size="20sp",
        )
        kutu.add_widget(baslik)

        aciklama = Label(
            text="Devam etmek için şifreli API key'i gir. Koda dokunmadan çözüp açalım.",
            size_hint_y=None,
            height=36,
            color=(0.75, 0.82, 0.90, 1),
            font_size="13sp",
        )
        aciklama.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        kutu.add_widget(aciklama)

        self.key_input = TextInput(
            hint_text="Şifreli API key'i buraya yapıştır...",
            multiline=False,
            size_hint_y=None,
            height=48,
            background_color=(0.11, 0.14, 0.20, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.25, 0.92, 0.78, 1),
            padding=[12, 14],
        )
        self.key_input.bind(on_text_validate=self.onayla_olayi)
        kutu.add_widget(self.key_input)

        buton_panel = BoxLayout(size_hint_y=None, height=48, spacing=10)
        onayla_btn = Button(
            text="ONAYLA VE AÇ",
            background_normal="",
            background_color=(0.05, 0.62, 0.48, 1),
            color=(1, 1, 1, 1),
            bold=True,
        )
        onayla_btn.bind(on_press=self.onayla_olayi)

        atla_btn = Button(
            text="KEY'SİZ DEVAM ET",
            size_hint_x=0.38,
            background_normal="",
            background_color=(0.20, 0.25, 0.34, 1),
            color=(0.9, 0.92, 0.96, 1),
        )
        atla_btn.bind(on_press=self.atla_olayi)

        buton_panel.add_widget(onayla_btn)
        buton_panel.add_widget(atla_btn)
        kutu.add_widget(buton_panel)

        self.uyari_lbl = Label(
            text="",
            size_hint_y=None,
            height=28,
            color=(1.0, 0.45, 0.45, 1),
            font_size="12sp",
        )
        kutu.add_widget(self.uyari_lbl)
        kutu.add_widget(BoxLayout())

        self.add_widget(kutu)

    def onayla_olayi(self, instance):
        sifreli_giris = self.key_input.text.strip()
        cozulmus_key = sifreli_key_coz(sifreli_giris, GIZLI_ANAHTAR)
        if not cozulmus_key:
            self.uyari_lbl.text = "Geçersiz veya bozuk şifreli API key."
            return
        self.groq_motoru.api_key_ayarla(cozulmus_key)
        self.uyari_lbl.text = ""
        self.on_tamam()

    def atla_olayi(self, instance):
        self.groq_motoru.api_key_ayarla("")
        self.uyari_lbl.text = ""
        self.on_tamam()


class KodBitApp(App):

    def build(self):
        self.title = ASISTAN_ADI
        self.groq_motoru = GroqMotoru()

        sm = ScreenManager()
        ana_ekran = Screen(name="ana")
        self.arayuz = KodBitArayuz(self.groq_motoru)
        ana_ekran.add_widget(self.arayuz)

        def sohbete_gec():
            sm.current = "ana"
            self.arayuz.baslat_senkron()

        key_ekrani = AcilisKeyEkrani(self.groq_motoru, sohbete_gec, name="key_girisi")
        sm.add_widget(key_ekrani)
        sm.add_widget(ana_ekran)
        sm.current = "key_girisi"
        return sm


if __name__ == "__main__":
    KodBitApp().run()