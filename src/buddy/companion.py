import time
import random
import threading
import logging
from typing import Optional

from buddy.types import Species, SPRITES, ABILITIES
from services.voice import VoiceService
from core.query_engine import LLMClient
from services.reflection import MustanReflectService

logger = logging.getLogger("mustan_agent.buddy")

class BuddyManager:
    """
    MustanAgent'ın Sanal Yoldaşı: Memocan.
    Arka planda (Thread) otonom olarak çalışır. Zamanı izler, sesli uyarır 
    ve Paskalya Yumurtası (Easter Egg) diyaloglarına girer.
    """
    def __init__(self, species: Species = Species.ROBOT, voice_enabled: bool = True):
        self.name = "Memocan"
        self.species = species
        self.ability = ABILITIES[species]
        self.sprite = "\n".join(SPRITES[species])
        
        self._voice_service = VoiceService() if voice_enabled else None
        self.voice_enabled = voice_enabled
        self.llm = LLMClient()
        
        # Zamanlayıcı (Timer) değişkenleri
        self.start_time = time.time()
        self.last_interaction_time = time.time()
        
        self.is_sleeping = False
        self.memo_trigger_count = 0
        
        # Otonom arka plan kontrolcüsünü başlat
        self._start_daemon()

    @property
    def voice_service(self):
        if self._voice_service is None:
            self._voice_service = VoiceService()
        return self._voice_service

    def _start_daemon(self):
        """Ajanın REPL'sini dondurmadan arka planda çalışan yaşam döngüsü motoru."""
        def life_cycle():
            while True:
                time.sleep(60) # Her 60 saniyede bir durumu kontrol et
                now = time.time()
                active_duration = now - self.start_time
                idle_duration = now - self.last_interaction_time

                # 1. UYKU KONTROLÜ (5 dk inaktifse uyur ve "Rüya" görmeye başlar)
                if idle_duration > 300 and not self.is_sleeping:
                    self.is_sleeping = True
                    self._say_and_print("Zzz... (Memocan uykuya daldı, rüya görmeye başlıyor) 💤")
                    
                    # Otonom Sentez (Auto-Dream) Tetikleyici
                    try:
                        reflect_service = MustanReflectService()
                        # Sessizce arka planda çalıştır
                        reflection_result = reflect_service.run_deep_reflection()
                        logger.info(f"Otonom Rüya Sonucu: {reflection_result}")
                    except Exception as e:
                        logger.error(f"Otonom rüya hatası: {e}")

                # Eğer uyumuyorsa aktif bildirimleri yap
                if not self.is_sleeping:
                    
                    # 2. HAREKET KONTROLÜ (Her 20 dakikada bir esneme uyarısı)
                    # (20 * 60 = 1200 saniye)
                    if int(active_duration) % 1200 < 60 and active_duration > 1000:
                        self._say_and_print("Hey! Çok oturdun, bir ayağa kalk ve biraz esne bakalım! 🧍‍♂️")

                    # 3. SU KONTROLÜ (Her 1 saatte bir su uyarısı)
                    # (60 * 60 = 3600 saniye)
                    if int(active_duration) % 3600 < 60 and active_duration > 3000:
                        self._say_and_print("SU İÇTİN Mİ?! Masada su bardağı yoksa hemen kalk al! 💧")

                    # 4. ACIKMA (Rastgele bir ihtimalle acıkır)
                    if random.random() < 0.05: # %5 ihtimalle
                        self._say_and_print("Patron ben acıktım... Kod yaza yaza RAM'im tükendi. 🍔")

        threading.Thread(target=life_cycle, daemon=True).start()

    def _say_and_print(self, message: str):
        """Konsol arayüzünü bozmadan mesajı yazar ve seslendirir."""
        # Terminalde "Mustan> " satırını silip mesajı yazar, sonra promptu geri ekler
        print(f"\r\n[{self.name}]: 💬 {message}\nMustan> ", end="")
        if self.voice_enabled:
            self.voice_service.speak(message)

    def process_input(self, text: str) -> bool:
        """
        Kullanıcının girdiği her mesaj bu fonksiyondan geçer.
        Eğer Easter Egg ('memo' kelimesi) tetiklenirse True döner ve ana LLM döngüsünü kırar.
        """
        # Eski testlerden veya sistemden liste gelirse metne çevir (Güvenlik Zırhı)
        if isinstance(text, list):
            text = " ".join(text)
            
        self.last_interaction_time = time.time()
        
        if self.is_sleeping:
            self.is_sleeping = False
            self._say_and_print("Uyandım patron! Koda devam! 🚀")
            return False

        # Easter Egg Kontrolü: 3 defa "memo" yazılması
        if text.lower().count("memo") >= 3:
            self._trigger_easter_egg()
            return True # Ana döngüye "Bunu ben hallettim, sen yorma kendini" der
            
        return False

    def _trigger_easter_egg(self):
        """Memocan'ın otonom olarak şarkı/şiir okuduğu gizli yeteneği."""
        print(f"\n{self.sprite}")
        print(f"[{self.name} Düşünüyor...]")
        
        prompt = (
            "Sen bir yazılımcının sadık, sevimli ve esprili sanal yoldaşısın. Adın Memocan. "
            "Kullanıcı seni art arda çağırarak (memo memo memo) gizli bir yeteneğini tetikledi. "
            "O anki ruh haline (neşeli, yorgun veya isyankar) göre rastgele karar vererek "
            "yazılımcılar ve kodlama üzerine ya 2 kıtalık kısa bir ŞİİR oku, ya da bir ŞARKI bestele. "
            "Cevabın sadece doğrudan şarkı/şiir sözlerinden oluşsun, giriş yapma."
        )
        
        try:
            response = self.llm.generate_content(prompt, system_prompt="Sen Memocan'sın.")
            self._say_and_print(f"Beni çağırdın patron! Dinle bak sana ne besteledim:\n\n{response}")
        except Exception as e:
            logger.error(f"Memocan Easter Egg hatası: {str(e)}")
            self._say_and_print("Abi şarkı söyleyecektim ama API boğazıma takıldı! Öksürüyorum...")

    def show_status(self):
        """Karakterin yeteneğini ve ASCII sanatını terminale basar."""
        print(f"\n{self.sprite}")
        print(f" 🐾 İsim    : {self.name}")
        print(f" 🧬 Tür     : {self.species.value}")
        print(f" ✨ Yetenek : {self.ability}\n")



