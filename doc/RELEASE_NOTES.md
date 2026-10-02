MustanAgent 3.3.1: kurulabilir CLI ve görev yürütme düzeltmeleri.

- Wheel giriş noktası, Python paketleri ve YAML kaynakları dağıtıma dahil edildi.
- Temel kurulum ile voice/browser/ide/desktop ek bağımlılıkları ayrıldı.
- Araç parametrelerinde JSON desteği ve Python girinti/iki nokta koruması eklendi.
- Görevler arasında durum sıfırlanır; her dosya değişikliği taze doğrulama gerektirir.
- Python dosyası yazılırken sözdizimi kontrolü uygulanır.
- Geçersiz, döngülü ve bilinmeyen bağımlılıklı planlar reddedilir.
- Başarısız anahtar kaydı, CLI çıkış kodları, yerel Ollama adresi ve IDE köprüsü düzeltildi.
- Proje kuralları model bağlamına dahil edilir; başarısız iş paketleri /repair ile yeniden çalıştırılabilir.
- README kurulum, sağlayıcı ayarları, sınırlar ve sorun giderme için yenilendi.

İndirme: wheel, kaynak dağıtımı (tar.gz) veya kaynak ZIP. Kurulum adımları README içinde.

MCP, tarayıcı ve masaüstü hizmetleri otonom araç döngüsüne bağlı değildir. Canlı API, ses ve masaüstü davranışı kullanıcının ortamında ayrıca denenmelidir. Maliyet bilgileri tahminidir.
