"""
MustanAgent v3.3 PRO - /deeplan komutu
dag_plan.json içindeki belirli bir WP'yi atomik checklist'e böler.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.query_engine import LLMClient
from core.config import settings
from models.datatypes import DAGPlan, WorkPackage, WPStatus

logger = logging.getLogger("mustan_agent.commands.deeplan")


DEEPLAN_SYSTEM_PROMPT = """Sen MustanAgent'ın Detaylı Planlama uzmanısın.
Sana bir iş paketi (WP) verilecek. Bu paketi kod yazmadan önce
geliştiricinin (veya Worker ajanın) takip edebileceği net, atomik checklist'e çevir.

Kurallar:
1. Her adım tek bir somut aksiyon olsun.
2. Adımlar sırayla numaralandırılsın.
3. Gerekli dosya yollarını, fonksiyon imzalarını ve kabul kriterlerini belirt.
4. Çıktın SADECE geçerli JSON olsun.

JSON şeması:
{
  "wp_id": "WP-001",
  "title": "...",
  "checklist": [
    {
      "step": 1,
      "action": "src/auth/login.py dosyasını oluştur",
      "details": "def authenticate(...)",
      "acceptance": "Dosya var ve py_compile geçiyor"
    }
  ],
  "estimated_files": ["src/auth/login.py"],
  "notes": "Opsiyonel notlar"
}
"""


def _get_memory_dir(memory_dir: Optional[str] = None) -> str:
    if memory_dir:
        return memory_dir
    try:
        base = settings.config.memory.base_dir
        return base or "Aimemory"
    except Exception:
        return "Aimemory"


def _load_dag(memory_dir: str) -> Optional[DAGPlan]:
    path = Path(memory_dir) / "dag_plan.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return DAGPlan.model_validate(data)
    except Exception as e:
        logger.error("dag_plan.json okunamadı: %s", e)
        return None


def _save_dag(dag: DAGPlan, memory_dir: str) -> None:
    path = Path(memory_dir) / "dag_plan.json"
    path.write_text(dag.model_dump_json(indent=2), encoding="utf-8")


def _extract_json(text: str) -> Optional[dict]:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    return None


def run_deeplan(wp_id: str, memory_dir: Optional[str] = None) -> bool:
    if not wp_id or not wp_id.strip():
        print("[-] /deeplan için WP id gerekli. Örnek: /deeplan WP-001")
        return False

    wp_id = wp_id.strip().upper()
    if not wp_id.startswith("WP-"):
        wp_id = f"WP-{int(wp_id):03d}" if wp_id.isdigit() else wp_id

    memory_dir = _get_memory_dir(memory_dir)
    os.makedirs(memory_dir, exist_ok=True)

    dag = _load_dag(memory_dir)
    if dag is None:
        print("[-] dag_plan.json bulunamadı. Önce /plan çalıştır.")
        return False

    if wp_id not in dag.nodes:
        print(f"[-] {wp_id} plan içinde yok. Mevcut id'ler: {', '.join(dag.nodes.keys())}")
        return False

    wp = dag.nodes[wp_id]
    print(f"[*] DeepPlan başlatılıyor → {wp_id}: {wp.title}")

    mind_path = Path(memory_dir) / "proje_mind.md"
    mind_map = mind_path.read_text(encoding="utf-8")[:8000] if mind_path.exists() else ""

    user_prompt = f"""İş Paketi:
ID: {wp.id}
Başlık: {wp.title}
Açıklama: {wp.description}
Bağımlılıklar: {wp.depends_on}
Etiketler: {wp.tags}

Proje Zihin Haritası (özet):
{mind_map or "(yok)"}

Bu iş paketini atomik checklist JSON'una çevir.
"""

    llm = LLMClient()
    try:
        response, _ = llm.generate_with_stats(
            prompt=user_prompt,
            system_prompt=DEEPLAN_SYSTEM_PROMPT,
        )
    except Exception as e:
        print(f"[-] LLM hatası: {e}")
        return False

    data = _extract_json(response)
    if not data:
        print("[-] Geçerli JSON alınamadı.")
        debug = Path(memory_dir) / f"deeplan_{wp_id}_raw.txt"
        debug.write_text(response, encoding="utf-8")
        return False

    if not isinstance(data, dict):
        print("[-] Checklist bir JSON nesnesi olmalı.")
        return False
    checklist = data.get("checklist") or []
    if not isinstance(checklist, list) or not checklist or not all(isinstance(item, dict) and item.get("action") for item in checklist):
        print("[-] Geçerli ve boş olmayan checklist gerekli.")
        return False
    lines = [
        f"# DeepPlan — {wp_id}",
        f"**Başlık:** {data.get('title') or wp.title}",
        f"**Oluşturulma:** {datetime.now().isoformat()}",
        "",
        "## Checklist",
        "",
    ]
    for item in checklist:
        step = item.get("step", "?")
        action = item.get("action", "")
        details = item.get("details", "")
        acceptance = item.get("acceptance", "")
        lines.append(f"### Adım {step}: {action}")
        if details:
            lines.append(f"- Detay: {details}")
        if acceptance:
            lines.append(f"- Kabul: {acceptance}")
        lines.append("")

    if data.get("estimated_files"):
        lines.append("## Tahmini Dosyalar")
        for f in data["estimated_files"]:
            lines.append(f"- `{f}`")
        lines.append("")

    if data.get("notes"):
        lines.append("## Notlar")
        lines.append(data["notes"])

    deeplan_dir = Path(memory_dir) / "deeplans"
    deeplan_dir.mkdir(exist_ok=True)
    md_path = deeplan_dir / f"{wp_id}.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")

    wp.updated_at = datetime.now()
    if "deeplan" not in wp.tags:
        wp.tags.append("deeplan")
    dag.nodes[wp_id] = wp
    dag.updated_at = datetime.now()
    _save_dag(dag, memory_dir)

    print(f"[+] DeepPlan kaydedildi → {md_path}")
    print(f"    Adım sayısı: {len(checklist)}")
    return True


if __name__ == "__main__":
    import sys
    wp = sys.argv[1] if len(sys.argv) > 1 else "WP-001"
    ok = run_deeplan(wp)
    raise SystemExit(0 if ok else 1)
