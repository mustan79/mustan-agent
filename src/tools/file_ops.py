import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any, Optional

# Loglama ayarı
logger = logging.getLogger("mustan_agent.tools.file_ops")

# ============================================================================
# 1. FILE READ (Dosya Okuma) Aracı
# ============================================================================
class FileReadInput(BaseModel):
    file_path: str = Field(..., description="Okunacak dosyanın mutlak veya göreceli yolu.")
    start_line: Optional[int] = Field(None, description="Okumaya başlanacak satır numarası (1-indeksli). Büyük dosyalarda kullanılır.")
    end_line: Optional[int] = Field(None, description="Okumanın biteceği satır numarası.")

class FileReadTool:
    """
    Belirtilen dosyayı okur ve LLM'in daha rahat referans verebilmesi için
    satır numaralarıyla (cat -n formatında) birlikte döndürür.
    İkili (binary) veya çok büyük dosyaların okunmasını engeller.
    """
    name = "Read"
    description = "Yerel dosya sisteminden bir dosyanın içeriğini okur."
    input_schema = FileReadInput

    @staticmethod
    def execute(input_data: FileReadInput, **kwargs: Any) -> str:
        path = Path(input_data.file_path).resolve()
        
        if not path.exists() or not path.is_file():
            logger.warning(f"Okuma başarısız: {path} bulunamadı.")
            return f"[-] Hata: Dosya bulunamadı -> {path}"
        
        try:
            # UTF-8 ile dosyayı oku, binary ise UnicodeDecodeError fırlatır
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            if not lines:
                return f"### Dosya: {path.name}\n(Dosya Boş)"
            
            # Satır sınırlarını ayarla (Token tasarrufu için)
            start = max(0, (input_data.start_line or 1) - 1)
            end = min(len(lines), input_data.end_line or len(lines))
            
            selected_lines = lines[start:end]
            
            # LLM'in smart_edit aracında doğru yeri bulabilmesi için satır numaraları ekle
            result = [f"### Dosya: {path} (Satırlar: {start+1}-{end})", "```python"]
            for i, line in enumerate(selected_lines, start=start + 1):
                # Örn: 14 | def process_data():
                result.append(f"{i:4d} | {line.rstrip()}")
            result.append("```")
            
            logger.info(f"[+] Dosya okundu: {path.name}")
            return "\n".join(result)
            
        except UnicodeDecodeError:
            logger.error(f"Binary dosya okunmaya çalışıldı: {path.name}")
            return f"[-] Hata: {path.name} okunamadı. Dosya ikili (binary - örn: resim, pdf) formatta olabilir."
        except Exception as e:
            return f"[-] Beklenmeyen Okuma Hatası ({path.name}): {str(e)}"


# ============================================================================
# 2. FILE WRITE (Dosya Yazma) Aracı
# ============================================================================
class FileWriteInput(BaseModel):
    file_path: str = Field(..., description="Oluşturulacak veya üzerine tamamen yazılacak dosyanın yolu.")
    content: str = Field(..., description="Dosyaya yazılacak tam ve eksiksiz içerik.")

class FileWriteTool:
    """
    Sıfırdan dosya oluşturmak veya bir dosyanın içeriğini baştan aşağı
    değiştirmek için kullanılır. Kısmi değişimler için SmartEdit kullanılmalıdır.
    """
    name = "Write"
    description = "Yeni bir dosya yazar veya mevcut bir dosyanın üzerine tamamen yazar."
    input_schema = FileWriteInput

    @staticmethod
    def execute(input_data: FileWriteInput, **kwargs: Any) -> str:
        path = Path(input_data.file_path).resolve()
        
        try:
            # Eğer dosyanın bulunması gereken alt klasörler yoksa (Örn: src/yeni/dosya.py) onları da yarat
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(input_data.content)
                
            logger.info(f"[+] Dosya yazıldı: {path.name}")
            return f"[+] Başarılı: '{path.name}' dosyası yerel diske başarıyla kaydedildi."
            
        except Exception as e:
            logger.error(f"Yazma hatası ({path.name}): {str(e)}")
            return f"[-] Yazma Hatası ({path.name}): {str(e)}"


