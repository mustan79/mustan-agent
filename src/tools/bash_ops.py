import os
import re
import subprocess
import logging
from pydantic import BaseModel, Field
from typing import Any

# Loglama ayarı
logger = logging.getLogger("mustan_agent.tools.bash_ops")

DESTRUCTIVE_PATTERNS = [
    (re.compile(r'\bgit\s+reset\s+--hard\b'), "Dikkat: Commit edilmemiş değişiklikleri çöpe atar!"),
    (re.compile(r'\bgit\s+push\b[^;&|\n]*\s+(--force|-f)\b'), "Dikkat: Uzak sunucudaki (Remote) git geçmişinin üzerine yazar!"),
    (re.compile(r'(^|[;&|\n]\s*)rm\s+-[a-zA-Z]*[rR]'), "Dikkat: Dosya/Klasörleri kalıcı ve özyinelemeli (recursive) olarak siler!"),
    (re.compile(r'\b(DROP|TRUNCATE)\s+(TABLE|DATABASE|SCHEMA)\b', re.IGNORECASE), "Dikkat: Veritabanı tablolarını yok eder!"),
]

def get_destructive_warning(command: str) -> str | None:
    """Komutun tehlikeli (yıkıcı) olup olmadığını regex ile denetler."""
    for pattern, warning in DESTRUCTIVE_PATTERNS:
        if pattern.search(command):
            return warning
    return None

# ============================================================================
# BASH (Terminal) Aracı
# ============================================================================
class BashInput(BaseModel):
    command: str = Field(
        ..., 
        description="Çalıştırılacak terminal (bash/shell/cmd) komutu. Örn: 'pip install moviepy', 'pytest tests/'"
    )
    timeout_ms: int = Field(
        default=120000, 
        description="Komutun maksimum çalışma süresi (Milisaniye). Varsayılan: 2 dakika (120000)."
    )

class BashTool:
    """
    İşletim sisteminin terminalinde komut çalıştırmak için kullanılır.
    Kullanıcının projelerini derlemek (build), paket yüklemek (pip/npm) veya 
    test scriptlerini çalıştırmak için otonom olarak kullanılabilir.
    """
    name = "Bash"
    description = "Sistemde bash (veya ortamın varsayılan shell'i) komutları çalıştırır."
    input_schema = BashInput

    @staticmethod
    def execute(input_data: BashInput, **kwargs: Any) -> str:
        command = input_data.command
        
        # 1. Tehlikeli Komut Kontrolü (Pre-Flight Check)
        warning = get_destructive_warning(command)
        if warning:
            logger.warning(f"Tehlikeli bash komutu denemesi: {command}")
            # Opsiyonel: MustanAgent'ın güvenlik ayarlarına (mode) göre burada işlemi 
            # doğrudan engelleyebilir veya sadece terminale uyarı basabiliriz.
            # Şimdilik uyarı metnini LLM'e iade edip onay mekanizmasına takılmasını sağlıyoruz:
            return f"[-] GÜVENLİK İHLALİ: Çalıştırmak istediğin komut '{command}' tehlikeli olarak işaretlendi.\nSebep: {warning}\nLütfen komutu silme veya zorlama içermeyecek şekilde yeniden yapılandır."

        try:
            # 2. Timeout ayarı (Milisaniyeyi saniyeye çevir)
            timeout_sec = input_data.timeout_ms / 1000.0
            logger.info(f"Bash komutu çalıştırılıyor: {command}")
            
            # 3. Güvenli Subprocess Çalıştırma
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout_sec,
                # cwd=kwargs.get("cwd", ".") # İleride ajan klasör değiştirirse kullanılabilir
            )
            
            # 4. Çıktıları Ayrıştırma ve Formatlama (LLM'e özel format)
            output_blocks = []
            
            if result.stdout:
                output_blocks.append(f"--- STDOUT ---\n{result.stdout.strip()}")
            if result.stderr:
                output_blocks.append(f"--- STDERR ---\n{result.stderr.strip()}")
                
            if result.returncode != 0:
                output_blocks.insert(0, f"[-] HATA: Komut '{result.returncode}' çıkış koduyla başarısız oldu.")
            else:
                output_blocks.insert(0, "[+] Başarılı: Komut sorunsuz tamamlandı.")
                
            return "\n\n".join(output_blocks)
            
        except subprocess.TimeoutExpired:
            logger.error(f"Zaman aşımı: {command} ({input_data.timeout_ms}ms)")
            return f"[-] HATA: Komut {input_data.timeout_ms}ms içinde tamamlanamadı (Zaman Aşımı). Eğer bu bir web sunucusu (örn: npm run dev) ise arkaplanda çalışması için ampersand (&) kullan."
        except Exception as e:
            logger.error(f"Beklenmeyen Bash Hatası: {str(e)}")
            return f"[-] Beklenmeyen Bash Sistem Hatası: {str(e)}"

