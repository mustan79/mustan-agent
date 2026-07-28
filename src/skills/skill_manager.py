import os
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger("mustan_agent.skills.skill_manager")

class SkillManager:
    """
    Ajanın yeteneklerini (Skills) yöneten sınıf.
    core_skills.yaml dosyasını ve custom/ dizinindeki özel yetenekleri yükler.
    """
    
    def __init__(self):
        # Dizin yollarını belirle (Bu dosyanın bulunduğu klasör taban alınır)
        self.current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        self.core_skills_file = self.current_dir / "core_skills.yaml"
        self.custom_skills_dir = self.current_dir / "custom"
        
        # Custom dizini yoksa oluştur
        self.custom_skills_dir.mkdir(parents=True, exist_ok=True)
        
        self.skills: List[Dict[str, Any]] = []
        self._load_all_skills()

    def _load_all_skills(self):
        """Tüm çekirdek ve özel (custom) yetenekleri belleğe yükler."""
        self.skills = []
        
        # 1. Çekirdek yetenekleri (YAML) yükle
        if self.core_skills_file.exists():
            try:
                with open(self.core_skills_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data and "skills" in data:
                        self.skills.extend(data["skills"])
                        logger.debug(f"{len(data['skills'])} çekirdek yetenek yüklendi.")
            except Exception as e:
                logger.error(f"core_skills.yaml okunamadı: {str(e)}")

        # 2. Kullanıcı tanımlı (Custom) yetenekleri yükle (.yaml veya .md)
        for file_path in self.custom_skills_dir.glob("*"):
            if file_path.is_file() and file_path.suffix in [".yaml", ".yml", ".md"]:
                try:
                    if file_path.suffix in [".yaml", ".yml"]:
                        with open(file_path, "r", encoding="utf-8") as f:
                            custom_data = yaml.safe_load(f)
                            if custom_data and "skills" in custom_data:
                                self.skills.extend(custom_data["skills"])
                    elif file_path.suffix == ".md":
                        # Basit Markdown yetenek yükleyici (Dosya adı komut, ilk satır açıklama)
                        with open(file_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                            if lines:
                                self.skills.append({
                                    "name": file_path.stem,
                                    "command": f"/{file_path.stem}",
                                    "description": lines.strip().replace("#", "").strip()
                                })
                except Exception as e:
                    logger.warning(f"Özel yetenek yüklenemedi ({file_path.name}): {str(e)}")

    def get_all_skills_text(self) -> str:
        """
        Niyet analizi (Intention Analysis) için LLM'e gönderilecek 
        formatlanmış yetenekler metnini üretir (Eski yetenekler_metni karşılığı).
        """
        if not self.skills:
            return "Kayıtlı yetenek bulunamadı."
            
        lines = []
        for skill in self.skills:
            command = skill.get("command", "")
            description = skill.get("description", "")
            if command and description:
                lines.append(f"* {command} : {description}")
                
        return "\n".join(lines)

