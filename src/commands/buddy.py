import logging
from typing import Optional
# (Buddy_instance çalışma zamanında enjekte edilecek)

logger = logging.getLogger("mustan_agent.commands.buddy")

def run_buddy(args: str, buddy_instance) -> bool:
    """
    /buddy komutu.
    Memocan'ın ayarlarını (ses, durum) değiştirmeni sağlar.
    """
    if not buddy_instance:
        print("[-] Buddy (Memocan) sistemi aktif değil.")
        return False

    args = args.strip().lower()

    if args == "mute":
        buddy_instance.voice_enabled = False
        print("\n[🔇] Memocan'ın sesi kapatıldı. Artık sadece yazacak.")
        return True
    elif args == "unmute":
        buddy_instance.voice_enabled = True
        print("\n[🔊] Memocan'ın sesi açıldı. Kulaklarını hazırla!")
        buddy_instance.voice_service.speak("Ses deneme bir iki! Geldim patron.")
        return True
    elif args == "status" or not args:
        buddy_instance.show_status()
        return True
    else:
        print("[-] Kullanım: /buddy [mute|unmute|status]")
        return False


