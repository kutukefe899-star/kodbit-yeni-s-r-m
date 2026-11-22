# Kod Bit

**Kod Bit**, Kivy arayüzlü, öğrenen ve bulut senkronizasyonlu kişisel bir asistan uygulamasıdır. Öğretilen kuralları ve soru-cevap eşleşmelerini yerel `kod_bit_hafiza.json` dosyasında ve `npoint.io` bulut JSON alanında tutar; yanıt üretirken hafızadaki bilgileri Groq API sistem talimatına aktarır.

## Özellikler
* **Kivy Grafik Arayüzü:** Öğretme (`OGRET`) ve soru sorma (`SOR`) panellerine sahip koyu temalı masaüstü/uygulama arayüzü.
* **Kalıcı + Bulut Hafıza:** Yerel `kod_bit_hafiza.json` ile `npoint.io` (`79a7f7f342542aa9d958`) arasında otomatik senkronizasyon.
* **Kimlik ve Kural Öğrenme:** Yaratıcı/yapımcı bilgisi güncelleme, `soru -> cevap` veya `soru = cevap` eşleşmeleri kaydetme ve genel kurallar ekleme.
* **Şifreli API Anahtarı:** Groq API anahtarını açık metin yerine şifreli (`SIFRELI_GROQ_KEY`) olarak saklayıp çalışma anında çözme.
* **Yedek Yanıt Mekanizması:** Groq erişilemezse veya anahtar yoksa kayıtlı hafıza eşleşmeleri ile Wikipedia / DuckDuckGo özetlerine düşebilme.

## Dosyalar
* `kod_bit.py`: Ana Kivy uygulaması, hafıza yöneticisi, Groq motoru ve şifreli API key çözücü.
* `key_sifrele.py`: Groq API anahtarını şifreleyip `SIFRELI_GROQ_KEY` çıktısı üreten yardımcı betik.
* `kod_bit_hafiza.json`: Yerel hafıza dosyası (`~/.local/share/kodbit/` altında oluşturulur).

## Kurulum ve Çalıştırma

### 1. API Anahtarını Şifreleme
* 'buradaki şifrele.py yi çalıştırıp arayüze yapıştırıp keyi şifreli halini alınız.Sonra ise o keyi kodbit e yapıştırınız'
