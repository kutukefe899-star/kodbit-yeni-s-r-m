import base64
from kivy.app import App
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

GIZLI_ANAHTAR = b"KodBit_Key_Gizli_2026!"

Window.clearcolor = (0.05, 0.07, 0.11, 1)
Window.minimum_width = 480
Window.minimum_height = 340


def api_key_sifrele(api_key: str, anahtar: bytes) -> str:
    ham = api_key.strip().encode("utf-8")
    karisik = bytearray()
    for i, b in enumerate(ham):
        k = anahtar[i % len(anahtar)]
        karisik.append((b ^ k ^ ((i * 13) & 0xFF)))
    return base64.b64encode(bytes(karisik)).decode("ascii")


class ApiSifreleArayuz(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=12, **kwargs)

        baslik = Label(
            text="[b]API Key Şifreleyici[/b]",
            markup=True,
            size_hint_y=None,
            height=36,
            halign="left",
            color=(0.25, 0.92, 0.78, 1),
            font_size="20sp",
        )
        baslik.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        self.add_widget(baslik)

        self.api_input = TextInput(
            hint_text="API Key gir (örnek: gsk_...)",
            multiline=False,
            size_hint_y=None,
            height=46,
            background_color=(0.11, 0.14, 0.20, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.25, 0.92, 0.78, 1),
            padding=[10, 13],
        )
        self.api_input.bind(on_text_validate=self.donustur_olayi)
        self.add_widget(self.api_input)

        donustur_btn = Button(
            text="DÖNÜŞTÜR",
            size_hint_y=None,
            height=48,
            background_normal="",
            background_color=(0.05, 0.62, 0.48, 1),
            color=(1, 1, 1, 1),
            bold=True,
        )
        donustur_btn.bind(on_press=self.donustur_olayi)
        self.add_widget(donustur_btn)

        self.cikti_input = TextInput(
            hint_text="Şifreli API Key burada görünecek...",
            readonly=True,
            multiline=True,
            size_hint_y=1,
            background_color=(0.09, 0.12, 0.17, 1),
            foreground_color=(0.55, 0.95, 0.80, 1),
            padding=[10, 10],
        )
        self.add_widget(self.cikti_input)

        alt_panel = BoxLayout(size_hint_y=None, height=42, spacing=10)
        kopyala_btn = Button(
            text="KOPYALA",
            background_normal="",
            background_color=(0.16, 0.48, 0.92, 1),
            color=(1, 1, 1, 1),
            bold=True,
        )
        kopyala_btn.bind(on_press=self.kopyala_olayi)

        self.durum_lbl = Label(
            text="API key yaz ve DÖNÜŞTÜR'e bas.",
            halign="right",
            valign="middle",
            color=(0.65, 0.72, 0.82, 1),
            font_size="12sp",
        )
        self.durum_lbl.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))

        alt_panel.add_widget(kopyala_btn)
        alt_panel.add_widget(self.durum_lbl)
        self.add_widget(alt_panel)

    def donustur_olayi(self, instance):
        ham_key = self.api_input.text.strip()
        if not ham_key:
            self.durum_lbl.text = "Önce bir API key gir."
            return
        sifreli = api_key_sifrele(ham_key, GIZLI_ANAHTAR)
        self.cikti_input.text = sifreli
        self.durum_lbl.text = "Dönüştürüldü."

    def kopyala_olayi(self, instance):
        if self.cikti_input.text.strip():
            Clipboard.copy(self.cikti_input.text.strip())
            self.durum_lbl.text = "Panoya kopyalandı."


class ApiSifreleApp(App):

    def build(self):
        self.title = "API Key Şifreleyici"
        return ApiSifreleArayuz()


if __name__ == "__main__":
    ApiSifreleApp().run()