### `src/tools/smart_edit.py`
import os
import tempfile
import subprocess
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any

# Loglama ayarı (Uygulama genelindeki loglayıcıyı kullanır)
logger = logging.getLogger("mustan_agent.tools.smart_edit")

# ============================================================================
# Pydantic Girdi Şeması (Input Schema)
# ============================================================================
class SmartEditInput(BaseModel):
    """
    LLM'in smart_edit aracını kullanırken doldurması zorunlu olan JSON şeması.
    """
    file_path: str = Field(
        ..., 
        description="Düzenlenecek hedef dosyanın mutlak veya göreceli yolu."
    )
    old_text: str = Field(
        ..., 
        description="Değiştirilecek olan mevcut kod bloğu. Dosyadaki girintiler (indentation) dahil BİREBİR aynı olmalıdır."
    )
    new_text: str = Field(
        ..., 
        description="Eski kodun yerine yazılacak olan yeni kod bloğu."
    )
    replace_all: bool = Field(
        default=False, 
        description="Eğer True ise, old_text'in dosyadaki tüm eşleşmelerini değiştirir. False ise tek eşleşme bekler."
    )


# ============================================================================
# Smart Edit Aracı Sınıfı (Structural Validation Destekli)
# ============================================================================
class SmartEditTool:
    """
    Structural Validation (Yapısal Doğrulama) destekli Akıllı Kod Düzenleme Aracı.
    Kodu diske fiziksel olarak kaydetmeden önce geçici bir dosyada (py_compile ile)
    sözdizimi (syntax) hatası içerip içermediğini kontrol eder. ("Pre-Flight Check")
    """
    
    name = "SmartEdit"
    description = (
        "Bir dosyadaki kodu güvenli bir şekilde değiştirir. "
        "Python dosyaları için diske yazmadan önce sözdizimi (syntax) testi yapar."
    )
    input_schema = SmartEditInput

    @staticmethod
    def execute(input_data: SmartEditInput, **kwargs: Any) -> str:
        """
        Değişiklik talebini alır, güvenli ortamda test eder ve ancak başarılıysa
        orijinal dosyaya yazar.
        """
        path = Path(input_data.file_path)
        if not input_data.old_text:
            return "[-] Hata: old_text boş olamaz."

        # 1. Dosya varlık kontrolü
        if not path.exists() or not path.is_file():
            logger.warning(f"SmartEdit başarısız: {path} bulunamadı.")
            return f"[-] Hata: '{input_data.file_path}' bulunamadı. Lütfen doğru yolu verdiğinden emin ol."

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # 2. Katı Bağlam (Strict Context) Eşleşme Kontrolü
            count = content.count(input_data.old_text)
            if count == 0:
                logger.warning(f"SmartEdit başarısız: '{path.name}' içinde old_text bulunamadı.")
                return (
                    "[-] Hata: 'old_text' dosya içinde bulunamadı. Lütfen boşlukların "
                    "ve girintilerin (indentation) birebir eşleştiğinden emin ol veya "
                    "önce 'Read' aracı ile dosyayı tekrar oku."
                )

            if count > 1 and not input_data.replace_all:
                logger.warning(f"SmartEdit başarısız: '{path.name}' içinde {count} adet eşleşme var.")
                return (
                    f"[-] Hata: 'old_text' dosya içinde {count} defa geçiyor. Hangi bloğun "
                    f"değiştirileceği belirsiz. Daha fazla bağlam (alt/üst satır) ekle veya "
                    f"'replace_all=True' kullan."
                )

            # 3. Metni bellekte (RAM) değiştir
            if input_data.replace_all:
                new_content = content.replace(input_data.old_text, input_data.new_text)
            else:
                new_content = content.replace(input_data.old_text, input_data.new_text, 1)

            # 4. Pre-Flight Check (Uçuş Öncesi Kontrol / Syntax Testi)
            # Sadece Python (.py) dosyaları için bu korumayı çalıştırıyoruz
            if path.suffix == ".py":
                try:
                    compile(new_content, str(path), "exec")
                except SyntaxError as exc:
                    return f"[-] Sözdizimi (Syntax) Hatası! Kod diske YAZILMADI. {exc}"

            # 5. Testi geçti! Başarılıysa asıl dosyaya güvenle yaz
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            logger.info(f"[+] SmartEdit başarılı: {path.name} güncellendi.")
            return f"[+] Başarılı: '{path.name}' dosyası güvenli bir şekilde güncellendi ve onaylandı."

        except Exception as e:
            logger.error(f"SmartEdit sırasında beklenmeyen hata ({path.name}): {str(e)}")
            return f"[-] Beklenmeyen Hata: {str(e)}"

