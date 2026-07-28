"""
MustanAgent v3.3+ - Intent Router
Doğal dili komuta eşler. Varsayılan yol LLM kullanmaz (token tasarrufu).
Gerekirse düşük maliyetli LLM fallback açılabilir.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Pattern, Tuple

logger = logging.getLogger("mustan_agent.core.intent_router")


class Intent(str, Enum):
    SCAN = "/scan"
    PLAN = "/plan"
    DEEPLAN = "/deeplan"
    OPERATE = "/operate"
    DOCTOR = "/doctor"
    SCOPE = "/scope"
    REFLECT = "/reflect"
    REWIND = "/rewind"
    BTW = "/btw"
    IDE = "/ide"
    STATUS = "/status"
    SUMMARY = "/summary"
    SET = "/set"
    WORKER = "/worker"
    VERIFY = "/verify"
    VOICE = "/voice"
    BUDDY = "/buddy"
    CHAT = "/chat"
    UNKNOWN = "/unknown"


@dataclass(frozen=True)
class IntentMatch:
    intent: Intent
    confidence: float
    args: str = ""
    source: str = "rule"  # rule | slash | llm_fallback
    raw: str = ""


@dataclass
class _Rule:
    intent: Intent
    patterns: List[Pattern[str]]
    weight: float = 1.0
    # Eşleşmeden argüman çıkarmak için grup adı (opsiyonel)
    arg_group: Optional[str] = None


def _compile(patterns: List[str]) -> List[Pattern[str]]:
    return [re.compile(p, re.IGNORECASE | re.UNICODE) for p in patterns]


# Öncelik: daha spesifik kurallar üstte değerlendirilir (liste sırası)
_RULES: List[_Rule] = [
    _Rule(
        Intent.DEEPLAN,
        _compile([
            r"\b(?:deeplan|deep\s*plan|detaylı\s*plan|wp[- ]?(\d{1,3}))\b",
            r"\b(?:iş\s*paketi|work\s*package)\s*(?:detay|aç|boz)",
        ]),
        weight=1.2,
    ),
    _Rule(
        Intent.PLAN,
        _compile([
            r"\b(?:plan\s*oluştur|planla|plan\s*çıkar|master\s*plan|görevleri\s*böl)\b",
            r"\b(?:iş\s*planı|yol\s*haritası|dag\s*plan)\b",
            r"^\s*plan\b",
        ]),
        weight=1.1,
    ),
    _Rule(
        Intent.OPERATE,
        _compile([
            r"\b(?:kod\s*yaz|dosya\s*(?:oluştur|ekle|düzenle|değiştir)|implement|implemente)\b",
            r"\b(?:operate|otonom\s*çalış|şunu\s*(?:yap|gerçekleştir)|düzelt|fix|bug\s*fix)\b",
            r"\b(?:fonksiyon\s*ekle|modül\s*ekle|class\s*yaz|refaktor)\b",
        ]),
        weight=1.15,
    ),
    _Rule(
        Intent.SCAN,
        _compile([
            r"\b(?:tara|scan|analiz\s*et|zihin\s*haritası|iskelet\s*çıkar|proje\s*oku)\b",
            r"\b(?:codebase\s*scan|ast\s*analiz)\b",
        ]),
    ),
    _Rule(
        Intent.DOCTOR,
        _compile([
            r"\b(?:doctor|sağlık|sistem\s*kontrol|uçuş\s*öncesi|eksik\s*paket|api\s*key\s*kontrol)\b",
            r"\b(?:ortam\s*sağlığı|dependency\s*check)\b",
        ]),
    ),
    _Rule(
        Intent.SUMMARY,
        _compile([
            r"\b(?:summary|özet|durum\s*özeti|ne\s*yapıldı|ilerleme|progress)\b",
            r"\b(?:bugün\s*ne|görev\s*özeti)\b",
        ]),
    ),
    _Rule(
        Intent.STATUS,
        _compile([
            r"\b(?:status|durum|token\s*durum|bütçe|harcama|stats)\b",
        ]),
    ),
    _Rule(
        Intent.SCOPE,
        _compile([
            r"\b(?:scope|kural\s*ekle|kuralları\s*(?:yaz|mühürle)|proje\s*kural)\b",
        ]),
    ),
    _Rule(
        Intent.REFLECT,
        _compile([
            r"\b(?:reflect|yansıt|ders\s*çıkar|reflection|içgörü)\b",
        ]),
    ),
    _Rule(
        Intent.REWIND,
        _compile([
            r"\b(?:rewind|geri\s*al|checkpoint|yedek\s*yükle)\b",
        ]),
    ),
    _Rule(
        Intent.VOICE,
        _compile([
            r"\b(?:voice|sesli|mikrofon|konuş|dinle|tts|stt)\b",
        ]),
    ),
    _Rule(
        Intent.VERIFY,
        _compile([
            r"\b(?:verify|doğrula|test\s*et|pytest|py_compile|qa)\b",
        ]),
    ),
    _Rule(
        Intent.WORKER,
        _compile([
            r"\b(?:worker|wp[- ]?\d{1,3}\s*(?:çalıştır|kodla)|iş\s*paketini\s*yap)\b",
        ]),
    ),
    _Rule(
        Intent.IDE,
        _compile([
            r"\b(?:ide|köprü|bridge|websocket\s*ide)\b",
        ]),
    ),
    _Rule(
        Intent.SET,
        _compile([
            r"\b(?:set\s+(?:provider|model|key|base_url)|sağlayıcı\s*değiş|model\s*değiş|api\s*key\s*ayarla)\b",
        ]),
    ),
    _Rule(
        Intent.BTW,
        _compile([
            r"\b(?:btw|by\s*the\s*way|arada\s*sor|kısa\s*soru)\b",
        ]),
    ),
    _Rule(
        Intent.BUDDY,
        _compile([
            r"\b(?:buddy|memocan|yoldaş)\b",
        ]),
    ),
]


class IntentRouter:
    """
    Kural tabanlı niyet yönlendirici.
    Slash komutları doğrudan geçer; doğal dil kurallarla eşlenir.
    """

    def __init__(self, enable_llm_fallback: bool = False):
        self.enable_llm_fallback = enable_llm_fallback
        self._rules = list(_RULES)

    def route(self, text: str) -> IntentMatch:
        raw = (text or "").strip()
        if not raw:
            return IntentMatch(Intent.UNKNOWN, 0.0, raw=raw)

        # 1) Zaten slash komut
        if raw.startswith("/"):
            return self._from_slash(raw)

        # 2) Kural motoru
        match = self._from_rules(raw)
        if match and match.confidence >= 0.45:
            logger.debug(
                "Intent rule: %s conf=%.2f args=%r",
                match.intent.value, match.confidence, match.args,
            )
            return match

        # 3) Opsiyonel LLM fallback (kapalı varsayılan)
        if self.enable_llm_fallback:
            fb = self._llm_fallback(raw)
            if fb:
                return fb

        return IntentMatch(Intent.CHAT, 0.4, args=raw, source="default", raw=raw)

    def _from_slash(self, raw: str) -> IntentMatch:
        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        try:
            intent = Intent(cmd)
        except ValueError:
            # /coder gibi alias
            aliases = {
                "/coder": Intent.OPERATE,
                "/run": Intent.OPERATE,
                "/health": Intent.DOCTOR,
                "/özet": Intent.SUMMARY,
            }
            intent = aliases.get(cmd, Intent.UNKNOWN)
        return IntentMatch(intent, 1.0, args=args, source="slash", raw=raw)

    def _from_rules(self, raw: str) -> Optional[IntentMatch]:
        best: Optional[IntentMatch] = None
        best_score = 0.0
        lower = raw.lower()

        for rule in self._rules:
            for pat in rule.patterns:
                m = pat.search(raw)
                if not m:
                    continue
                # Uzun eşleşme + weight → confidence
                span = m.end() - m.start()
                score = min(1.0, (span / max(len(raw), 1)) * 2.5 * rule.weight)
                score = max(score, 0.5 * rule.weight)  # taban
                if score > best_score:
                    args = self._extract_args(raw, rule.intent, m)
                    best_score = score
                    best = IntentMatch(
                        intent=rule.intent,
                        confidence=min(score, 0.99),
                        args=args,
                        source="rule",
                        raw=raw,
                    )
        return best

    def _extract_args(self, raw: str, intent: Intent, match: re.Match) -> str:
        """Komuta gidecek argümanı kaba şekilde ayıkla."""
        # WP-001 benzeri
        wp = re.search(r"WP-?\s*(\d{1,3})", raw, re.I)
        if intent in (Intent.DEEPLAN, Intent.WORKER, Intent.VERIFY) and wp:
            num = wp.group(1).zfill(3)
            return f"WP-{num}"

        # Dosya yolu
        path = re.search(
            r"([a-zA-Z0-9_./\\-]+\.py|[a-zA-Z0-9_./\\-]+/)",
            raw,
        )
        if intent in (Intent.SCAN, Intent.VERIFY, Intent.OPERATE) and path:
            # Tüm cümleyi argüman vermek genelde daha iyi (operate/plan için)
            if intent == Intent.SCAN:
                return path.group(1)
            return raw

        # plan / operate / scope: tüm metin argüman
        if intent in (
            Intent.PLAN, Intent.OPERATE, Intent.SCOPE,
            Intent.BTW, Intent.SET, Intent.SUMMARY,
        ):
            # Komut benzeri kelimeleri kırp
            cleaned = re.sub(
                r"^\s*(?:lütfen|please)?\s*",
                "",
                raw,
                flags=re.I,
            )
            return cleaned.strip()

        return raw.strip()

    def _llm_fallback(self, raw: str) -> Optional[IntentMatch]:
        """Kapalı varsayılan; açılırsa kısa prompt ile tek token-ish cevap."""
        try:
            from core.query_engine import LLMClient
            llm = LLMClient()
            system = (
                "Sadece şu komutlardan birini yaz, başka bir şey yazma: "
                + ", ".join(i.value for i in Intent if i != Intent.UNKNOWN)
            )
            text, _ = llm.generate_with_stats(
                prompt=raw,
                system_prompt=system,
                use_rag=False,
                temperature=0.0,
            )
            cmd = text.strip().split()[0].lower()
            if not cmd.startswith("/"):
                cmd = "/" + cmd
            try:
                intent = Intent(cmd)
            except ValueError:
                return None
            return IntentMatch(intent, 0.7, args=raw, source="llm_fallback", raw=raw)
        except Exception as e:
            logger.warning("Intent LLM fallback başarısız: %s", e)
            return None


# Singleton erişim
_router: Optional[IntentRouter] = None


def get_intent_router(enable_llm_fallback: bool = False) -> IntentRouter:
    global _router
    if _router is None:
        _router = IntentRouter(enable_llm_fallback=enable_llm_fallback)
    return _router
