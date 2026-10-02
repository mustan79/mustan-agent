# MustanAgent 3.3.1

Türkçe komutlarla proje inceleme, planlama ve dosya düzenleme yapan terminal asistanı. Gemini, OpenAI, OpenRouter ve Ollama bağlantılarını destekler. Python 3.10 veya üstü gerekir.

[İndir / GitHub Releases](https://github.com/mustan79/mustan-agent/releases/latest) · [Kaynak kod](https://github.com/mustan79/mustan-agent) · [Değişiklikler](doc/CHANGELOG.md)

## Hızlı kurulum

Temel kurulum mikrofon, masaüstü veya tarayıcı bileşenlerini gerektirmez. PyPI yayını henüz yapılmadı; aşağıdaki komutlar GitHub sürümünü kurar.

### Windows (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install "https://github.com/mustan79/mustan-agent/releases/download/v3.3.1/mustan_agent-3.3.1-py3-none-any.whl"
.\.venv\Scripts\mustan-agent.exe --version
.\.venv\Scripts\mustan-agent.exe --help
```

Sanal ortamı etkinleştirmek isterseniz `.\.venv\Scripts\Activate.ps1` kullanın. PowerShell etkinleştirmeyi engelliyorsa yukarıdaki doğrudan dosya yollarıyla devam edebilirsiniz.

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "https://github.com/mustan79/mustan-agent/releases/download/v3.3.1/mustan_agent-3.3.1-py3-none-any.whl"
mustan-agent --help
```

### ZIP veya kaynak koddan kurulum

Releases sayfasından `mustan-agent-3.3.1-source.zip` indirin, açın ve klasörde sanal ortam oluşturun. Ardından `python -m pip install .` ve `mustan-agent --help` çalıştırın.

Geliştirme kurulumu:

```bash
git clone https://github.com/mustan79/mustan-agent.git
cd mustan-agent
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev,ide]"
python -m pytest -q
```

## İlk kullanım

Aracı üzerinde çalışacağınız projenin klasöründe başlatın. Etkinleştirilmiş sanal ortamda `mustan-agent`, Windows'ta doğrudan kurduğunuz `.venv\Scripts\mustan-agent.exe` yolu kullanılabilir.

```text
mustan-agent
/set provider gemini
/set model <sağlayıcınızın erişilebilir model adı>
/set key GEMINI_API_KEY <anahtarınız>
/doctor
/scan .
/scope Mevcut dosyaları önce oku. Türkçe açıklamalar kullan.
/operate hello.py oluştur; merhaba yazdırsın. Dosyayı okuyup çalıştırarak doğrula.
```

API anahtarları işletim sistemi anahtarlığında saklanır. Anahtarlık servisi bulunmayan sistemlerde ortam değişkeni kullanın. `/set key` terminalde görünür; ekran paylaşırken ortam değişkenini tercih edin. Anahtarları dosyalara veya Git'e eklemeyin.

| Sağlayıcı | Anahtar |
| --- | --- |
| Gemini | `GEMINI_API_KEY` veya `GOOGLE_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| OpenRouter | `OPENROUTER_API_KEY` |
| Yerel Ollama | Gerekmez |
| Ollama Cloud | `OLLAMA_API_KEY` |

PowerShell'de `$env:GEMINI_API_KEY="..."`, Linux/macOS'ta `export GEMINI_API_KEY="..."` kullanabilirsiniz. Model adı seçtiğiniz sağlayıcıyla uyumlu olmalıdır; sağlayıcı değişiminden sonra `/set model` çalıştırın.

Yerel Ollama için önce Ollama'yı ayrıca kurup seçtiğiniz modeli indirin ve sunucuyu başlatın:

```text
/set provider ollama
/set model <indirdiğiniz model>
/set base_url http://localhost:11434/v1
/doctor
```

Ollama Cloud için `/set provider ollama_cloud`, erişilebilir model ve anahtarınızı girin. Varsayılan bulut adresi `https://ollama.com/v1` olur.

## Komutlar

| Komut | İşlev |
| --- | --- |
| `/help`, `/list` | Yardım |
| `/doctor` | Bağımlılık ve aktif sağlayıcı anahtarı kontrolü; bağlantı testi yapmaz |
| `/scan [dizin]` | Python AST analizi ve proje haritası |
| `/plan <hedef>` | Bağımlılıkları doğrulanan iş paketleri oluşturma |
| `/deeplan WP-001` | İş paketine ayrıntılı checklist |
| `/worker WP-001` | İş paketini yürütme |
| `/repair WP-001` | Başarısız paketi deneme sınırı içinde yeniden yürütme |
| `/operate <görev>` | Plan, dosya/terminal araçları ve sonuç kontrolü |
| `/verify [WP-001 veya dosya.py]` | Python derleme veya pytest doğrulaması |
| `/scope [kurallar]` | Kuralları gösterme veya ekleme; model bağlamına dahil edilir |
| `/status`, `/summary`, `/telemetry` | Plan, token ve tahmini maliyet raporları |
| `/reflect` | Oturumdan dersler çıkarma |
| `/rewind <id>` | Önceden hazırlanmış `Aimemory/snapshots/<id>` yedeğini geri yükleme |
| `/btw <soru>` | Kısa soru |
| `/voice [status/test/on/off]` | İsteğe bağlı ses hizmeti |
| `/ide [start/status/stop]` | Yerel WebSocket köprüsü |
| `/buddy` | Memocan bilgileri |

`projeyi tara`, `özet ver`, `durum ne` gibi tanınan doğal dil istekleri yerel kurallarla yönlendirilir. Karmaşık isteklerde doğrudan `/operate` veya `/plan` kullanın. Çıkış: `exit`, `quit`, `/quit`.

Komutlar tek seferlik de çalıştırılabilir:

```bash
mustan-agent scan .
mustan-agent operate "README.md dosyasını incele ve kurulum bölümünü düzelt"
mustan-agent verify hello.py
```

Çıkış kodları: `0` başarı, `1` işlem hatası, `2` bilinmeyen komut. IDE köprüsünü açık tutmak için etkileşimli oturumda `/ide start` kullanın.

## İsteğe bağlı özellikler

Kaynak klasöründen:

```bash
python -m pip install ".[voice]"
python -m pip install ".[browser]"
python -m playwright install chromium
python -m pip install ".[ide]"
python -m pip install ".[desktop]"
```

İndirilen wheel için `python -m pip install "./mustan_agent-3.3.1-py3-none-any.whl[voice]"` kullanılabilir. `all` tüm ek bileşenleri kurar. Linux'ta mikrofon kurulumu PortAudio geliştirme paketleri gerektirebilir; PyAudio hatası temel CLI kullanımını etkilemez. STT Google hizmetine ses gönderir ve internet gerektirir. TTS sesi işletim sisteminizde kurulu seslere bağlıdır.

Tarayıcı ve masaüstü hizmetlerinin kodu vardır; bu sürümün otonom araç döngüsüne bağlı araçlar `read_file`, `write_file`, `smart_edit` ve `bash` ile sınırlıdır. IDE eklentisi bu depoda yoktur. MCP modülü taslak durumundadır ve etkin bir protokol entegrasyonu olarak sunulmaz.

## Veriler, doğrulama ve sınırlar

Çalışma klasöründe `mustan_settings.json` ile `Aimemory/` oluşur. Planlar, proje haritası, kurallar, oturum kayıtları ve telemetri burada saklanır; API anahtarları bu dosyalara yazılmaz. Bu veriler modele bağlam olarak gönderilebilir. Proje klasörünüzü yedekleyin veya Git ile takip edin.

Python yazma/düzenleme işlemleri sözdizimi kontrolünden geçer. Değiştirilen dosyanın yeniden okunması tamamlanma koşuludur; bu kontrol, davranışın doğru olduğunu kanıtlamaz. İsteğinize test çalıştırma kabul kriteri ekleyin ve çıktıları gözden geçirin. Terminal aracı kullanıcı hesabınızın yetkileriyle çalışır; uygulama sandbox değildir. Yıkıcı komut filtresi sınırlı bir ek korumadır.

Maliyetler sağlayıcı bazlı sabit tahminlerdir; modelin gerçek faturasını temsil etmez. Günlük bütçe kontrolü tahmine dayanır. Sağlayıcı panelinizden ayrıca limit belirleyin. `/rewind` otomatik snapshot oluşturmaz ve mevcut dosyaların üzerine yazar.

## Sorun giderme

- **Komut bulunamıyor:** Sanal ortamı etkinleştirin veya `.venv/Scripts/mustan-agent.exe` / `.venv/bin/mustan-agent` yolunu kullanın.
- **Anahtar yok / kimlik doğrulama hatası:** `/doctor` çalıştırın; aktif sağlayıcı, anahtar ve model adını kontrol edin.
- **Anahtarlığa kayıt başarısız:** Ortam değişkeni kullanın; Linux'ta masaüstü Secret Service erişimini kontrol edin.
- **Ollama bağlantısı yok:** Sunucuyu başlatın; `/set base_url http://localhost:11434/v1` çalıştırın.
- **Görev adım sınırına takılıyor:** İsteği küçültün; logları `Aimemory/mustan_agent.log` içinde inceleyin.
- **Mikrofon hazır değil:** `voice` ekini kurun ve işletim sistemi mikrofon izinlerini kontrol edin.

## Test ve dağıtım

```bash
python -m pytest -q
python -m build
python -m twine check dist/*
```

GitHub Actions Windows/Linux ve Python 3.10/3.12/3.13 üzerinde testleri çalıştırır, wheel kurulumunu denetler ve dağıtım dosyaları üretir. `v*` etiketi gönderildiğinde testler başarılı olursa GitHub Release oluşturur. Testler dış model API'lerini çağırmaz. Canlı model, mikrofon ve masaüstü başarısı kullanıcının ortamına bağlıdır.

MIT lisansı. Katkı için [CONTRIBUTING](doc/CONTRIBUTING.md) dosyasına bakın.
