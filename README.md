# MustanAgent v3.3 PRO 🚀

MustanAgent, gelişmiş otonom yapısı temel alınarak "Harness Engineering" standartlarında inşa edilmiş, çoklu ajan (Multi-Agent) destekli bir **Otonom Yazılım Geliştirme Asistanıdır**.

Projenizi bir metin yığını olarak değil, AST (Abstract Syntax Tree) destekli semantik bir zihin haritası olarak okur; DAG tabanlı planlar yapar ve kendi yazdığı kodu test ederek hatalarını giderir.

## 🌟 Neler Yeni (v3.3 PRO)
* **MustanVault:** API anahtarlarınız artık güvende. İşletim sisteminin yerel Credential Manager / Keychain kasasında şifrelenir.
* **Çoklu Ajan (Multi-Agent) Mimarisi:** Orkestratör (Coordinator), Mimar (Planner), İşçi (Worker), Testçi (Verifier) ve Keşifçi (Explorer) olmak üzere 5 farklı uzman ajan.
* **Akıllı Analiz (AST):** Projeyi Regex yerine Python derleyicisi mantığıyla (AST) tarar. Token bütçesini tüketmeden projenin zihin haritasını çıkarır.
* **Structural Validation (SmartEdit):** Kod dosyanıza yazılmadan önce `py_compile` ile test edilir. Bozuk kod diskinizi asla kirletmez.
* **MCP (Model Context Protocol) Desteği:** Dış dünyadaki veritabanlarına ve araçlara standart protokol ile bağlanır.
* **Sesli Kodlama (Voice Mode):** Mikrofonunuzu dinleyerek doğal dilden koda dönüşüm yapar.

## 🛠️ Kurulum

Proje kök dizininde aşağıdaki komutları çalıştırarak asistanı sisteminize küresel bir CLI aracı olarak kurabilirsiniz:

```bash
# 1. Geliştirme ortamı için bağımlılıkları yükleyin
pip install -r requirements.txt

# 2. Paketi terminale tanıtmak için yükleyin (Düzenlenebilir mod)
pip install -e .

# 3. Playwright (Web Testleri ve Vision UI) tarayıcılarını kurun
playwright install
```

## 🚀 Kullanım

Terminalinizden projenizin bulunduğu klasöre gidin ve aracı başlatın:
```bash
mustan-agent
```

### Temel Komutlar (Slash Commands)
* `/doctor` : Sistemdeki eksik paketleri, API erişimlerini ve ortam sağlığını kontrol eder. *(Uçuş öncesi ilk bunu çalıştırın!)*
* `/scan` : Projeyi okur ve `Aimemory/proje_mind.md` içerisine AST iskeletini çıkarır.
* `/plan <hedef>` : Scan sonucuna bakarak yapılacak işleri (DAG) atomik parçalara (WP) böler.
* `/deeplan <wp-id>` : Belirli bir iş paketini kodlayıcının anlayacağı checklist haline getirir.
* `/coder <wp-id>` : Kodu yazar, değiştirir, terminalde test eder ve hata çıkarsa kendini onarır.
* `/scope <kurallar>` : Projeye özel kalıcı geliştirme kuralları mühürler.

## 🔒 Güvenlik Notu
`mustan-agent doctor` çalıştırıldığında sizden API anahtarı isteyebilir. Ajan, bu anahtarı asla `.env` dosyasında tutmaz, sisteminizin şifreli anahtarlığına mühürler.

# Projede token maliyet hesabı yapılmaktadır.
# Örnek Maliyetler (Gemini 1.5 Pro veya OpenAI baz alınmıştır)
# 1M Token Input = $1.25, 1M Token Output = $5.00
COST_PER_1K_INPUT = 0.00125
COST_PER_1K_OUTPUT = 0.00500
    Her LLM çağrısında Aimemory/stats.json dosyasını günceller.
    Harcanan dolar maliyetini döndürür.

