import json
import logging
import asyncio
import threading
from typing import Optional, Dict, Any

try:
    import websockets
except ImportError:
    websockets = None

logger = logging.getLogger("mustan_agent.bridge.ide_server")

class MustanBridge:
    """
    MustanAgent IDE Entegrasyon Köprüsü.
    Arka planda hafif bir WebSocket sunucusu çalıştırarak VS Code / JetBrains gibi 
    editörlerden gelen 'Aktif Dosya' ve 'İmleç Konumu' verilerini toplar.
    Tamamen opsiyoneldir.
    """
    _instance = None

    def __init__(self, port: int = 8765):
        self.port = port
        self.is_running = False
        self.connected_ide = False
        
        # IDE'den gelen canlı bağlam verileri
        self.active_file: Optional[str] = None
        self.selection: Optional[str] = None
        
        self.server_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @classmethod
    def get_instance(cls):
        """Singleton deseni ile sistemde tek bir köprü çalışmasını garantiler."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def _ws_handler(self, websocket, path):
        """IDE'den gelen JSON mesajlarını dinleyen asenkron dinleyici."""
        self.connected_ide = True
        logger.info("IDE MustanBridge'e başarıyla bağlandı.")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    event_type = data.get("type")
                    
                    if event_type == "cursor_move":
                        self.active_file = data.get("file")
                        self.selection = data.get("selection")
                except json.JSONDecodeError:
                    continue
        except websockets.exceptions.ConnectionClosed:
            logger.info("IDE bağlantısı koptu.")
        finally:
            self.connected_ide = False
            self.active_file = None
            self.selection = None

    def _run_server(self):
        """Kendi event loop'unda sunucuyu ayağa kaldırır."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        start_server = websockets.serve(self._ws_handler, "localhost", self.port)
        self._loop.run_until_complete(start_server)
        self._loop.run_forever()

    def start(self) -> bool:
        """Sunucuyu arka planda (Daemon) başlatır."""
        if websockets is None:
            print("[-] 'websockets' kütüphanesi eksik. Lütfen 'pip install websockets' çalıştırın.")
            return False
            
        if self.is_running:
            return False
            
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        self.is_running = True
        return True

    def get_ide_context(self) -> str:
        """
        Koordinatör ajanın (JIT Prompting) sohbete ekleyeceği canlı IDE bağlamı.
        """
        if not self.connected_ide or not self.active_file:
            return ""
            
        ctx = f"### [CANLI IDE BAĞLAMI]\nKullanıcı şu an IDE'sinde `{self.active_file}` dosyasını açık tutuyor."
        if self.selection:
            ctx += f"\nKullanıcının IDE'de seçtiği kod/satır:\n```\n{self.selection}\n```"
        return ctx + "\n"

