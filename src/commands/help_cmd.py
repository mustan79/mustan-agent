"""
MustanAgent v3.3+ - /help ve /list
"""

from __future__ import annotations

HELP_TEXT = """
MustanAgent — Komut Listesi
===========================

Temel
  /help, /list          Bu liste
  /doctor               Ortam ve API anahtari kontrolu
  /status               Token, butce, DAG ozeti
  /summary              Ilerleme ozeti (DAG + maliyet)
  /telemetry            Caller bazli maliyet (varsa)

Proje
  /scan [dizin]         AST zihin haritasi
  /plan <hedef>         DAG is paketleri uret
  /deeplan <WP-id>      Is paketini checklist yap
  /operate <gorev>      Otonom kod/gorev dongusu
  /worker <WP-id>       Belirli WP'yi calistir
  /verify [WP|dosya]    Test / py_compile
  /repair <WP-id>       Self-repair analiz (+ retry)

Kural / bellek
  /scope [kurallar]     Proje kurallarini goster veya yaz
  /reflect              Oturum dersleri / karar gunlugu
  /rewind <id>          Snapshot geri yukle

Sistem
  /set provider <ad>    gemini|openai|openrouter|ollama|ollama_cloud
  /set model <ad>
  /set key <NAME> <val> Vault'a API key
  /set base_url <url>   Ollama endpoint

Diger
  /voice [test|status|on|off]   Sesli mod
  /ide [start|status|stop]      IDE WebSocket koprusu (etkilesimli oturum)
  /btw <soru>                   Ana akisi bozmadan kisa soru
  /buddy                        Memocan ayarlari

Dogal dil ornekleri
  "projeyi tara"
  "login icin plan olustur"
  "masaüstüne deneme.txt yaz"   → operate
  "ozet ver" / "durum ne"

Cikis: exit | quit | /quit
""".strip()


def run_help(args: str = "") -> bool:
    print(HELP_TEXT)
    return True


