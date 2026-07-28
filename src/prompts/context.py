
import logging
from typing import Optional

# Temel sistem kimlikleri ve şablonlar
from prompts.system import COORDINATOR_SYSTEM_PROMPT, WORKER_SYSTEM_PROMPT, EXPLORER_SYSTEM_PROMPT, PLANNER_SYSTEM_PROMPT
from prompts.templates import build_worker_prompt, build_intention_prompt

# Hafıza ve işletim sistemi katmanlarından bağlam çekimi
from memory.context import build_system_context
from memory.workspace_md import get_workspace_rules
from memory.rag_buffer import get_relevant_context

from core.config import settings
from bridge.ide_server import MustanBridge

logger = logging.getLogger("mustan_agent.prompts.context")

class PromptBuilder:
    """
    MustanAgent'ın JIT (Just-In-Time) Prompting motorudur.
    Ajanın rolüne (Worker, Planner, Explorer) göre ihtiyaç duyduğu 
    büyük bağlamı (Git, Kurallar, RAG, Hata Geçmişi) dinamik olarak birleştirir.
    """
    
    @staticmethod
    def build_coordinator_prompt(skills_text: str) -> str:
        """
        Ana orkestratör ajanı için yetenekleri ve sistem bağlamını birleştirir.
        """
        base_prompt = COORDINATOR_SYSTEM_PROMPT
        os_context = build_system_context()
        
        # IDE Köprüsünden canlı veriyi çek
        ide_context = MustanBridge.get_instance().get_ide_context()
        
        prompt = f"{base_prompt}\n\n{os_context}\n"
        if ide_context:
            prompt += f"\n{ide_context}\n"
            
        return f"{prompt}\nMEVCUT YETENEKLER:\n{skills_text}"

    @staticmethod
    def build_intention_analysis_prompt(user_input: str, skills_text: str) -> str:
        """
        Niyet analizi için şablonu (templates.py) bağlamla doldurur.
        """
        return build_intention_prompt(user_input=user_input, skills_text=skills_text)

    @staticmethod
    def build_worker_system_prompt() -> str:
        """
        İşçi ajan (Coder) için katı kuralları, OS/Git bağlamını ve 
        projenin kalıcı kurallarını (scope) tek potada eritir.
        """
        sys_context = build_system_context()
        workspace_rules = get_workspace_rules()
        
        prompt = f"{WORKER_SYSTEM_PROMPT}\n\n{sys_context}\n"
        if workspace_rules:
            prompt += f"\nPROJE ÖZEL KURALLARI:\n{workspace_rules}\n"
            
        return prompt

    @staticmethod
    def build_worker_task_prompt(
        task_description: str, 
        target_file: Optional[str] = None,
        action_history: Optional[list] = None,
        last_error: str = ""
    ) -> str:
        """
        WorkerAgent'a verilecek asıl görevi, geçmiş hatalarla birlikte hazırlar.
        RAG (Semantic Search) kullanarak görevle eşleşen kod iskeletlerini de ekler.
        """
        # Şablonu kullanarak görevi ve hataları oluştur
        task_prompt = build_worker_prompt(
            task_description=task_description,
            target_file=target_file,
            action_history=action_history,
            last_error=last_error
        )
        
        # (ilk denemeyse) RAG bağlamını enjekte et
        if not action_history and not last_error:
            logger.debug("Görev için RAG (Zihin Haritası) bağlamı aranıyor...")
            relevant_code = get_relevant_context(query=task_description)
            if relevant_code:
                task_prompt += f"\n\n### REFERANS İÇİN KOD İSKELETLERİ (RAG):\n{relevant_code}\n"
                
        return task_prompt

    @staticmethod
    def build_planner_prompt(goal: str, mind_map_text: str) -> str:
        """
        Planlama ajanı için zihin haritasını (Tüm proje iskeletini) ve hedefi birleştirir.
        """
        return f"{PLANNER_SYSTEM_PROMPT}\n\nPROJE ZİHİN HARİTASI:\n{mind_map_text}\n\nHEDEF: {goal}"

    @staticmethod
    def build_explorer_prompt() -> str:
        """Keşifçi ajan için salt okunur sistem promptu."""
        return f"{EXPLORER_SYSTEM_PROMPT}\n\n{build_system_context()}"

