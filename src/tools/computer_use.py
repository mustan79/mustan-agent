import os
import base64
import logging
import threading
from io import BytesIO
from typing import Optional, Dict, Any

# Güvenli donanım kontrol kütüphaneleri
import pyautogui
import keyboard
from PIL import ImageGrab
from pydantic import BaseModel, Field

from models.datatypes import ToolExecutionResult

logger = logging.getLogger("mustan_agent.tools.computer_use")

# PyAutoGUI Güvenlik Ayarları (Harness Engineering Standartları)
# Fareyi ekranın en köşesine (0,0) çekersen ajan anında çöker ve kontrolü sana verir.
pyautogui.FAILSAFE = True 
pyautogui.PAUSE = 0.5 # Her eylem arasına 0.5 saniye insani gecikme (Animasyonlu)

class ComputerUseInput(BaseModel):
    """ComputerUseTool için gerekli olan Pydantic veri şeması."""
    action: str = Field(..., description="Yapılacak eylem: 'screenshot', 'mouse_move', 'left_click', 'right_click', 'type_text', 'press_key'")
    x: Optional[int] = Field(default=None, description="Fare hareketi için X koordinatı")
    y: Optional[int] = Field(default=None, description="Fare hareketi için Y koordinatı")
    text: Optional[str] = Field(default=None, description="type_text için yazılacak metin")
    key: Optional[str] = Field(default=None, description="press_key için basılacak tuş (örn: 'enter', 'esc', 'ctrl')")

class ComputerUseTool:
    """
    MustanAgent Bilgisayar Kontrol (Computer Use) Aracı.
    Ajanın ekran görüntüsü almasını, fareyi hareket ettirmesini ve klavyeyi kullanmasını sağlar.
    Acil durum freni (Kill-Switch) olarak 'ESC' tuşu dinlenir.
    """
    input_schema = ComputerUseInput
    
    _kill_switch_active = False

    @classmethod
    def _monitor_kill_switch(cls):
        """Arka planda ESC tuşunu dinleyerek ajanın donanım yetkisini anında keser."""
        if keyboard.is_pressed('esc'):
            cls._kill_switch_active = True
            logger.warning("[!] ESC ACİL DURUM FRENİ TETİKLENDİ! Bilgisayar kontrolü durduruldu.")

    @classmethod
    def execute(cls, input_data: ComputerUseInput) -> str:
        # Her eylemden önce Kill-Switch kontrolü yap
        cls._kill_switch_active = False
        threading.Thread(target=cls._monitor_kill_switch, daemon=True).start()

        action = input_data.action.lower()
        
        try:
            if cls._kill_switch_active:
                return "[-] İŞLEM İPTAL EDİLDİ: Kullanıcı ESC tuşuna basarak acil durum frenini çekti."

            # 1. EKRAN GÖRÜNTÜSÜ ALMA (Ajanın Gözleri)
            if action == "screenshot":
                # Ekranı yakala ve bellekte Base64 formatına çevir (LLM'e göndermek için)
                screenshot = ImageGrab.grab()
                buffered = BytesIO()
                screenshot.save(buffered, format="PNG", optimize=True)
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                
                screen_width, screen_height = pyautogui.size()
                
                # Ajan, Base64 görseli multimodal olarak işleyip buton koordinatlarını bulacak
                return f"[+] Ekran görüntüsü alındı (Çözünürlük: {screen_width}x{screen_height}).\nGörsel Verisi (Base64): data:image/png;base64,{img_str[:100]}... [İÇERİK KISALTILDI]"

            # 2. FARE HAREKETİ
            elif action == "mouse_move":
                if input_data.x is None or input_data.y is None:
                    return "[-] Hata: mouse_move eylemi için 'x' ve 'y' koordinatları zorunludur."
                
                # İnsani bir hareket ivmesi (easeInOutQuad) ile fareyi belirtilen noktaya götür
                pyautogui.moveTo(input_data.x, input_data.y, duration=0.8, tween=pyautogui.easeInOutQuad)
                return f"[+] Fare başarıyla ({input_data.x}, {input_data.y}) koordinatlarına taşındı."

            # 3. TIKLAMA İŞLEMLERİ
            elif action == "left_click":
                pyautogui.click(button='left')
                return "[+] Sol tık yapıldı."
                
            elif action == "right_click":
                pyautogui.click(button='right')
                return "[+] Sağ tık yapıldı."
            # 4. KLAVYE KULLANIMI (Metin Yazma)
            elif action == "type_text":
                if not input_data.text:
                    return "[-] Hata: type_text eylemi için 'text' parametresi zorunludur."
                # Tuş vuruşları arasına 0.05 sn koyarak anti-bot sistemlerine yakalanmayı önle
                pyautogui.write(input_data.text, interval=0.05)
                return f"[+] Metin yazıldı: '{input_data.text}'"

            # 5. KLAVYE KULLANIMI (Özel Tuşlara Basma)
            elif action == "press_key":
                if not input_data.key:
                    return "[-] Hata: press_key eylemi için 'key' parametresi zorunludur."
                pyautogui.press(input_data.key)
                return f"[+] '{input_data.key}' tuşuna basıldı."

            else:
                return f"[-] Bilinmeyen eylem: {action}. Geçerli eylemler: screenshot, mouse_move, left_click, right_click, type_text, press_key"

        except pyautogui.FailSafeException:
            return "[-] GÜVENLİK İHLALİ: Fare ekranın köşesine götürüldüğü için PyAutoGUI güvenlik sistemi (FailSafe) işlemi durdurdu."
        except Exception as e:
            return f"[-] Bilgisayar kontrolü sırasında hata: {str(e)}"


