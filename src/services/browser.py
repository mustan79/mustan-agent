import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Playwright senkron API (pip install playwright)
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    raise ImportError("Playwright bulunamadı. Lütfen 'pip install playwright' ve 'playwright install' komutlarını çalıştırın.")

logger = logging.getLogger("mustan_agent.services.browser")

class BrowserService:
    """
    Playwright tabanlı Web Otomasyon Servisi.
    Ajanın arka planda (headless) web sayfalarını test etmesini, 
    DOM içeriğini okumasını ve "Vision API" için ekran görüntüsü (Screenshot) almasını sağlar.
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.timeout_ms = 30000  # 30 saniye zaman aşımı
        
    def fetch_and_screenshot(self, url: str, output_dir: str = "Aimemory/screenshots") -> Dict[str, Any]:
        """
        Belirtilen URL'ye gider, sayfanın metin içeriğini çeker ve 
        sayfanın tam ekran görüntüsünü diske kaydeder.
        """
        os.makedirs(output_dir, exist_ok=True)
        safe_name = "".join(c if c.isalnum() else "_" for c in url)[:50]
        screenshot_path = Path(output_dir) / f"{safe_name}.png"
        
        result = {
            "url": url,
            "success": False,
            "text_content": "",
            "screenshot_path": None,
            "error": None
        }

        logger.info(f"BrowserService başlatılıyor. Hedef: {url}")
        
        try:
            with sync_playwright() as p:
                # Chromium tabanlı gizli tarayıcıyı başlat
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(viewport={'width': 1280, 'height': 800})
                page = context.new_page()
                
                # Sayfaya git ve yüklenmesini bekle
                page.goto(url, timeout=self.timeout_ms, wait_until="networkidle")
                
                # Görsel doğrulama (Visual Regression) için ekran görüntüsü al
                page.screenshot(path=str(screenshot_path), full_page=True)
                result["screenshot_path"] = str(screenshot_path)
                
                # LLM'in okuyabilmesi için sayfadaki tüm okunabilir metni çek
                result["text_content"] = page.evaluate("document.body.innerText").strip()
                result["success"] = True
                
                browser.close()
                logger.info(f"[+] Tarayıcı testi başarılı. Ekran görüntüsü: {screenshot_path.name}")
                
        except PlaywrightTimeout:
            err_msg = "Zaman aşımı (Timeout). Sayfa yüklenemedi."
            logger.error(err_msg)
            result["error"] = err_msg
        except Exception as e:
            err_msg = f"Tarayıcı hatası: {str(e)}"
            logger.error(err_msg)
            result["error"] = err_msg
            
        return result

