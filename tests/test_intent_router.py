"""Intent Router birim testleri."""

from core.intent_router import IntentRouter, Intent


class TestIntentRouter:

    def setup_method(self):
        self.router = IntentRouter(enable_llm_fallback=False)

    def test_slash_plan(self):
        m = self.router.route("/plan login ekle")
        assert m.intent == Intent.PLAN
        assert m.args == "login ekle"
        assert m.source == "slash"
        assert m.confidence == 1.0

    def test_natural_plan(self):
        m = self.router.route("bu proje için bir plan oluştur")
        assert m.intent == Intent.PLAN
        assert m.confidence >= 0.45

    def test_natural_operate(self):
        m = self.router.route("src altına login fonksiyonu ekle ve kod yaz")
        assert m.intent == Intent.OPERATE

    def test_natural_scan(self):
        m = self.router.route("projeyi tara zihin haritası çıkar")
        assert m.intent == Intent.SCAN

    def test_deeplan_wp(self):
        m = self.router.route("WP-3 için deeplan yap")
        assert m.intent == Intent.DEEPLAN
        assert "WP-003" in m.args or "WP-3" in m.args.upper().replace(" ", "")

    def test_doctor(self):
        m = self.router.route("sistem sağlığını kontrol et doctor")
        assert m.intent == Intent.DOCTOR

    def test_summary(self):
        m = self.router.route("bugünkü ilerleme özetini ver")
        assert m.intent == Intent.SUMMARY

    def test_chat_fallback(self):
        m = self.router.route("merhaba nasılsın bugün hava güzel")
        assert m.intent in (Intent.CHAT, Intent.UNKNOWN)

    def test_empty(self):
        m = self.router.route("   ")
        assert m.intent == Intent.UNKNOWN

