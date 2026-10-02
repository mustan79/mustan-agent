# Değişiklik Günlüğü (Changelog)

## [3.3.1] - 2026-10-02

- Kurulabilir wheel, CLI giriş noktası ve paket kaynakları düzeltildi.
- Temel bağımlılıklar ile isteğe bağlı ses/tarayıcı/IDE/masaüstü bileşenleri ayrıldı.
- Araç girdileri, taze dosya doğrulaması, görev durumu ve Python yazma koruması düzeltildi.
- Geçersiz planlar reddedilir; /repair ve proje kuralları yürütmeye bağlandı.
- Ollama yerel adresi, anahtar kayıt sonucu, günlük bütçe sıfırlama ve IDE köprüsü düzeltildi.
- Kurulum README'si, regresyon testleri ve GitHub Actions dağıtım akışı eklendi.
- Önceki MCP kaydı bir taslağı ifade eder; bu sürümde aktif MCP entegrasyonu yoktur.

## [v3.3.0 PRO] - 2026-04-04
### Eklenenler (Added)
* **MustanVault:** API anahtarları için işletim sistemi düzeyinde (Keychain/Credential Manager) güvenli şifreleme altyapısı eklendi.
* **Multi-Agent Mimarisi:** Görevler Explorer, Planner, Worker ve Verifier olmak üzere 4 farklı uzman ajana bölündü.
* **Structural Validation (SmartEdit):** Kodlar diske yazılmadan önce `py_compile` ile test edilerek Syntax (sözdizimi) hataları engellendi.
* **AST Analyzer:** Proje taramaları (`/scan`) Regex yerine Python Abstract Syntax Tree (AST) motoruyla semantik hale getirildi.
* **MCP (Model Context Protocol):** Dış sunuculara ve veritabanlarına bağlantı için standart protokol istemcisi eklendi.
* **Voice Mode:** Mikrofon yakalama ve Google hizmeti üzerinden Speech-to-Text entegrasyonu sağlandı.

### Değiştirilenler (Changed)
* `MustanAgent` monolitik ana sınıfı parçalandı ve `AgentRuntime` (AgentZero döngüsü) olarak yeniden modellendi.
* Tüm veri yapıları standartlaştırıldı ve `Pydantic` modellerine taşındı.

### Kaldırılanlar (Removed)
* İlkel `.mustanagent_env` düz metin dosyası kullanımı güvenlik nedeniyle tamamen kaldırıldı.



