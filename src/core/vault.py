import os
import logging

try:
    import keyring
except ImportError:
    raise ImportError("keyring kütüphanesi bulunamadı. Lütfen 'pip install keyring' komutunu çalıştırın.")

logger = logging.getLogger("mustan_agent.core.vault")

class MustanVault:
    """
    API anahtarları gibi hassas verileri işletim sisteminin yerel ve şifreli 
    kasasında (Windows Credential Manager / macOS Keychain) saklayan güvenlik modülü.
    """
    SERVICE_NAME = "MustanAgent_v3.3_PRO"

    @classmethod
    def get_secret(cls, key_name: str) -> str:
        """
        İstenen anahtarı önce çevre değişkenlerinden (Environment Variables),
        eğer orada yoksa işletim sisteminin güvenli kasasından çeker.
        """
        # 1. Öncelik: Çevre değişkenleri (Geçici oturumlar veya Docker/CI için)
        secret = os.getenv(key_name)
        if secret:
            return secret
            
        # 2. Öncelik: Güvenli Kasa (Local geliştirme için)
        try:
            vault_secret = keyring.get_password(cls.SERVICE_NAME, key_name)
            return vault_secret if vault_secret else ""
        except Exception as e:
            logger.error(f"MustanVault erişim hatası ({key_name}): {str(e)}")
            return ""

    @classmethod
    def set_secret(cls, key_name: str, secret_value: str) -> bool:
        """
        Yeni bir API anahtarını güvenli kasaya kaydeder.
        """
        try:
            keyring.set_password(cls.SERVICE_NAME, key_name, secret_value)
            logger.info(f"[+] {key_name} MustanVault kasasına güvenle kaydedildi.")
            return True
        except Exception as e:
            logger.error(f"MustanVault kayıt hatası ({key_name}): {str(e)}")
            return False

    @classmethod
    def delete_secret(cls, key_name: str) -> bool:
        """
        Kayıtlı bir anahtarı kasadan siler.
        """
        try:
            keyring.delete_password(cls.SERVICE_NAME, key_name)
            logger.info(f"[-] {key_name} MustanVault kasasından silindi.")
            return True
        except keyring.errors.PasswordDeleteError:
            return False
        except Exception as e:
            logger.error(f"MustanVault silme hatası ({key_name}): {str(e)}")
            return False

