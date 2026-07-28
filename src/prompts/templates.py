# ============================================================================
# Dinamik Şablon Oluşturucular (Dynamic Prompt Templates)
# ============================================================================

def build_worker_prompt(
    task_description: str, 
    target_file: str = "", 
    action_history: list = None, 
    last_error: str = "",
    workspace_rules: str = ""
) -> str:
    """
    Kodu yazacak olan WorkerAgent (İşçi Ajan) için o anki görevin ve
    varsa önceki hataların bağlamını oluşturur Kısır Döngü Kırıcı).
    """
    prompt = f"GÖREV: {task_description}\n"
    
    if target_file:
        prompt += f"Hedef Dosya: {target_file}\n"
        
    if workspace_rules:
        prompt += f"\nPROJE ÖZEL KURALLARI:\n{workspace_rules}\n"

    # Ajanın önceki denemeleri ve hataları
    if action_history and len(action_history) > 0:
        prompt += "\nÖNCEKİ DENEMELERİN (Bunlar işe yaramadı, farklı bir strateji dene):\n"
        for i, action in enumerate(action_history, 1):
            prompt += f"{i}. Deneme: {action}\n"
            
    if last_error:
        prompt += f"\n[ÖNEMLİ UYARI - ÖNCEKİ DENEME HATASI]:\nYazdığın son kod şu hatayı verdi:\n{last_error}\nLütfen bu hatayı analiz et ve aynı hatayı tekrarlamayacak GÜNCELLENMİŞ bir çözüm üret.\n"

    return prompt

def build_intention_prompt(user_input: str, skills_text: str) -> str:
    """
    Koordinatör ajanın Niyet Analizi (Intention Analysis) yapması için kullanılır.
    Kullanıcının ne yapmak istediğini (Komut mu, Sohbet mi) belirler.
    """
    return f"""Sen bir niyet analiz motorusun. Kullanıcının girdisini analiz et.
Aşağıdaki yetenek listesine bakarak, kullanıcının bir aracı/komutu tetiklemek mi istediğine yoksa sadece sohbet mi ettiğine karar ver.

MEVCUT YETENEKLER VE ARAÇLAR:
{skills_text}

KURAL:
1. Eğer girdi açıkça yukarıdaki yeteneklerden/komutlardan birini ima ediyorsa SADECE komutu dön (Örn: /scan veya /coder WP-001). Başka hiçbir kelime yazma.
2. Eğer girdi normal bir sohbet, soru veya bağlam eklenmiş bir analiz isteği ise (veya yetenek listesiyle eşleşmiyorsa) SADECE 'CHAT' yaz.

KULLANICI GİRDİSİ: {user_input}
YANIT:"""


