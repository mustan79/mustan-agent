# MustanAgent v3.3 PRO'ya Katkıda Bulunmak

MustanAgent projesine ilgi duyduğunuz için teşekkürler! Bu proje, otonom yazılım geliştirme standartlarını "Harness Engineering" prensipleriyle yeniden tanımlamayı amaçlamaktadır.

## Neler Yapabilirsiniz?
* **Yetenek (Skill) Ekleme:** `src/skills/custom/` dizinine yeni YAML veya MD formatında yetenekler ekleyebilirsiniz.
* **Araç (Tool) Geliştirme:** Ajanın dış dünyayla etkileşimini artıracak (örn: veritabanı okuyucu) araçlar kodlayabilirsiniz.
* **Hata Giderme (Bug Fixes):** Test odamızda (`tests/`) başarısız olan senaryoları onarabilirsiniz.

## Geliştirme Ortamı Kurulumu
1. Projeyi forklayın ve klonlayın.
2. Sanal ortamınızı (venv) oluşturun.
3. `python -m pip install -e ".[dev,ide]"` ile geliştirme ve test bağımlılıklarını kurun.
4. `python -m pytest -q` çalıştırın. Testler API anahtarlarını kullanmaz; canlı servisler mock edilir.
5. `python -m build` ve `python -m twine check dist/*` ile paketlemeyi doğrulayın.

## Kod Standartları
* Tüm kodlar **Type-Safe** olmalı ve `Pydantic` şemaları kullanılmalıdır.
* Otonom döngüyü bozabilecek `print()` veya `input()` gibi bloklayıcı komutlar yerine ajan araçlarını (`ToolExecutionResult`) kullanın.
* Yeni eklenen her özellik için `tests/` klasörüne bir `pytest` senaryosu eklenmesi zorunludur.


