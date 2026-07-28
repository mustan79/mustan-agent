# Değişiklik Günlüğü (Changelog)

## [v3.3.0 PRO] - 2026-04-04
### Eklenenler (Added)
* **MustanVault:** API anahtarları için işletim sistemi düzeyinde (Keychain/Credential Manager) güvenli şifreleme altyapısı eklendi.
* **Multi-Agent Mimarisi:** Görevler Explorer, Planner, Worker ve Verifier olmak üzere 4 farklı uzman ajana bölündü.
* **Structural Validation (SmartEdit):** Kodlar diske yazılmadan önce `py_compile` ile test edilerek Syntax (sözdizimi) hataları engellendi.
* **AST Analyzer:** Proje taramaları (`/scan`) Regex yerine Python Abstract Syntax Tree (AST) motoruyla semantik hale getirildi.
* **MCP (Model Context Protocol):** Dış sunuculara ve veritabanlarına bağlantı için standart protokol istemcisi eklendi.
* **Voice Mode:** Doğal dil komutları için yerel Speech-to-Text entegrasyonu sağlandı.

### Değiştirilenler (Changed)
* `MustanAgent` monolitik ana sınıfı parçalandı ve `AgentRuntime` (AgentZero döngüsü) olarak yeniden modellendi.
* Tüm veri yapıları standartlaştırıldı ve `Pydantic` modellerine taşındı.

### Kaldırılanlar (Removed)
* İlkel `.mustanagent_env` düz metin dosyası kullanımı güvenlik nedeniyle tamamen kaldırıldı.



