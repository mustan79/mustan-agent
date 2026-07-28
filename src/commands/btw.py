import logging
from core.query_engine import LLMClient

logger = logging.getLogger("mustan_agent.commands.btw")

def run_btw(question: str) -> bool:
    """
    /btw (By the way) komutu.
    Kullanıcının ana iş akışını (context) bozmadan bağımsız bir soru sormasını sağlar.
    """
    if not question.strip():
        print("[-] Lütfen bir soru sorun. Örn: /btw Python 3.12 switch-case nasıldı?")
        return False

    print(f"\n[>] Yan Soru (BTW) Analiz Ediliyor: '{question}'")
    
    # Yeni, izole bir LLMClient çağrısı yapıyoruz (Ana bellek dizisine eklenmez)
    llm = LLMClient()
    system_prompt = (
        "Sen uzman bir yazılım danışmanısın. Kullanıcı, ana projesini kodlarken "
        "araya girip bağımsız bir 'yan soru' (side-question) sordu. "
        "Kısa, net ve doğrudan kod/çözüm odaklı cevap ver. Konuyu uzatma."
    )
    
    try:
        response, _ = llm.generate_with_stats(prompt=question, system_prompt=system_prompt)
        print(f"\n[💡 Bu Arada (BTW)]:\n{response}\n")
        return True
    except Exception as e:
        logger.error(f"/btw komutu başarısız: {str(e)}")
        print(f"[-] Yan soru cevaplanamadı: {str(e)}")
        return False


