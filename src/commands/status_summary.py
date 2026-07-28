import sys
import json
from pathlib import Path
from core.query_engine import LLMClient

def _print_token_stats():
    stats_file = Path("Aimemory") / "stats.json"
    if stats_file.exists():
        try:
            with open(stats_file, "r") as f:
                data = json.load(f)
                print(f" Toplam Harcanan Token: {data.get('total_prompt',0) + data.get('total_completion',0):,}")
                print(f" Tahmini Maliyet      : ${data.get('total_cost_usd',0.0):.4f}")
        except:
            print(" Token İstatistikleri : Okunamadı")
    else:
        print(" Token İstatistikleri : Henüz kullanım yok.")

def run_status() -> bool:
    print("\n" + "="*50)
    print(" 📡 MustanAgent v3.3 PRO - Sistem Durumu")
    print("="*50)
    print(f" OS Modeli        : {sys.platform}")
    
    # LLMClient artık Singleton ve modeli dinamik çekiyor
    client = LLMClient()
    active_model, _ = client._get_active_model_and_provider()
    
    print(f" LLM Modeli       : {active_model}")
    _print_token_stats()
    print("="*50)
    return True

def run_summary() -> bool:
    print("\n[>] Seans Özeti Çıkarılıyor...")
    client = LLMClient()
    
    stats_file = Path("Aimemory") / "stats.json"
    token_str = ""
    if stats_file.exists():
        with open(stats_file, "r") as f:
            data = json.load(f)
            token_str = f"Şu ana kadar harcanan maliyet: ${data.get('total_cost_usd',0.0):.4f}"

    prompt = f"Seansın genel gidişatını tek bir paragrafta özetle. {token_str}"
    response = client.generate_content(prompt, system_prompt="Sen bir proje asistanısın.")
    print(f"\n[📝 Seans Özeti]:\n{response}\n")
    return True

def run_telemetry_report(memory_dir: str = "Aimemory") -> bool:
    from core.telemetry import get_telemetry
    store = get_telemetry(memory_dir)
    s = store.summary_today()
    print("—— Telemetry (bugün) ——")
    print(f"Çağrı: {s['total_calls']} | Token: {s['total_tokens']} | "
          f"${s['total_cost_usd']:.4f} | Hata: {s['fail_count']}")
    print("\nCaller bazlı:")
    for caller, v in s.get("by_caller", {}).items():
        print(
            f"  {caller}: {v['calls']} çağrı | "
            f"{v['tokens']} tok | ${v['cost_usd']:.4f} | fail={v['fail']}"
        )
    return True

