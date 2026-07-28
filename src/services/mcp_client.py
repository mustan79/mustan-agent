import os
import json
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("mustan_agent.services.mcp_client")

class MCPClient:
    """
    Model Context Protocol (MCP) İstemcisi.
    MustanAgent'ın dış dünyadaki yetenekleri (Veritabanları, harici araçlar) 
    okuyabilmesini sağlayan standart iletişim protokolü.
    """
    
    def __init__(self, config_path: str = ".mcp.json"):
        # MCP sunucularının kaydedildiği yapılandırma dosyası
        self.config_path = Path(os.getcwd()) / config_path
        self.servers: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Yerel .mcp.json dosyasını okur (varsa)."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("mcpServers", {})
            except Exception as e:
                logger.error(f"MCP Konfigürasyon okuma hatası: {str(e)}")
        return {}

    def get_registered_servers(self) -> List[str]:
        """Kayıtlı MCP sunucularının (Örn: 'sqlite', 'github') listesini döner."""
        return list(self.servers.keys())

    def call_mcp_tool(self, server_name: str, tool_name: str, args: List[str]) -> str:
        """
        Kayıtlı bir MCP sunucusunu StdIO (standart girdi/çıktı) üzerinden tetikler
        ve sonucunu LLM'in okuması için string olarak döner.
        """
        if server_name not in self.servers:
            return f"[-] Hata: '{server_name}' adında bir MCP sunucusu kayıtlı değil."

        server_config = self.servers[server_name]
        command = server_config.get("command")
        server_args = server_config.get("args", [])
        env = server_config.get("env", {})
        
        # Mevcut ortam değişkenlerini kopyala ve üzerine MCP env'lerini ekle
        run_env = os.environ.copy()
        run_env.update(env)

        full_cmd = [command] + server_args + [tool_name] + args
        
        logger.info(f"MCP Tool tetikleniyor: {server_name} -> {tool_name}")
        
        try:
            # MCP sunucularını güvenli ve zaman aşımı (timeout) kısıtlı çalıştır
            result = subprocess.run(
                full_cmd,
                env=run_env,
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode != 0:
                logger.warning(f"MCP Sunucu Hatası ({server_name}): {result.stderr}")
                return f"[-] MCP Hatası ({server_name}): {result.stderr.strip()}"
                
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            return f"[-] Zaman Aşımı: MCP sunucusu ({server_name}) 15 saniye içinde yanıt vermedi."
        except Exception as e:
            logger.error(f"MCP Çalıştırma Hatası: {str(e)}")
            return f"[-] Sistem Hatası: MCP aracı çalıştırılamadı. Detay: {str(e)}"


