import logging
from bridge.ide_server import MustanBridge

logger = logging.getLogger("mustan_agent.commands.ide")

def run_ide(args: str) -> bool:
    """
    /ide komutu.
    Kullanıcının IDE köprüsünü (WebSocket) başlatmasını ve durumunu görmesini sağlar.
    """
    bridge = MustanBridge.get_instance()
    args = args.strip().lower()

    if args == "start":
        if bridge.start():
            print("\n[🔌 MustanBridge Aktif!]")
            print(f"IDE'nizdeki (VS Code) eklentinizi 'ws://localhost:{bridge.port}' adresine bağlayabilirsiniz.\n")
        else:
            if bridge.is_running:
                print("[~] MustanBridge zaten çalışıyor.")
                return True
            print(f"[-] MustanBridge başlatılamadı: {bridge.last_error}")
            return False
        return True

    elif args == "stop":
        bridge.stop()
        return True
        
    elif args == "status" or not args:
        print("\n" + "="*40)
        print(" 🌉 MustanBridge (IDE Entegrasyonu)")
        print("="*40)
        print(f" Sunucu Durumu : {'Aktif (Çalışıyor)' if bridge.is_running else 'Kapalı'}")
        if bridge.is_running:
            print(f" IDE Bağlantısı: {'[+] BAĞLI' if bridge.connected_ide else '[-] BEKLENİYOR'}")
            print(f" Aktif Dosya   : {bridge.active_file or 'Yok'}")
        print("="*40 + "\n")
        return True
        
    else:
        print("[-] Kullanım: /ide [start|status]")
        return False



