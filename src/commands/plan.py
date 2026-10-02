"""
MustanAgent v3.3 PRO - /plan komutu
Hedefi atomik iş paketlerine böler ve dinamik DAG (dag_plan.json) olarak kaydeder.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

from core.query_engine import LLMClient
from core.config import settings
from models.datatypes import DAGPlan, WorkPackage, WPStatus

logger = logging.getLogger("mustan_agent.commands.plan")


PLAN_SYSTEM_PROMPT = """Sen MustanAgent'ın Baş Mimarı'sın.
Görevin: Verilen hedefi ve proje zihin haritasını inceleyerek
yönlendirilmiş döngüsüz çizge (DAG) mantığında atomik iş paketleri üretmek.

Kurallar:
1. Her iş paketi tek bir net çıktı üretmeli (bir dosya, bir test, bir config vb.).
2. depends_on listesinde sadece gerçekten önce bitmesi gereken WP id'leri olsun.
3. Döngü (cycle) oluşturma.
4. Id formatı: WP-001, WP-002, ... (sıralı).
5. Mümkün olduğunca paralel çalışabilecek bağımsız paketler oluştur.
6. Çıktın SADECE geçerli bir JSON olsun. Başka açıklama yazma.

JSON şeması:
{
  "goal": "kullanıcının hedefi",
  "nodes": [
    {
      "id": "WP-001",
      "title": "Kısa başlık",
      "description": "Detaylı ne yapılacağı",
      "depends_on": [],
      "tags": ["backend"]
    }
  ]
}
"""


def _load_mind_map(memory_dir: str) -> str:
    mind_path = Path(memory_dir) / "proje_mind.md"
    if mind_path.exists():
        try:
            return mind_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("proje_mind.md okunamadı: %s", e)
    return ""


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


def _build_dag_from_llm(raw: dict, goal: str) -> DAGPlan:
    if not isinstance(raw, dict):
        raise ValueError("Plan must be a JSON object")
    plan = DAGPlan(goal=raw.get("goal") or goal)
    nodes_data = raw.get("nodes") or raw.get("work_packages") or []
    for i, item in enumerate(nodes_data, start=1):
        if not isinstance(item, dict):
            continue
        wp_id = item.get("id") or f"WP-{i:03d}"
        if not re.fullmatch(r"WP-\d{3}", wp_id) or wp_id in plan.nodes:
            raise ValueError(f"Invalid or duplicate work package: {wp_id}")
        wp = WorkPackage(
            id=wp_id,
            title=item.get("title") or item.get("name") or wp_id,
            description=item.get("description") or item.get("desc") or "",
            depends_on=item.get("depends_on") or item.get("dependencies") or [],
            tags=item.get("tags") or [],
            status=WPStatus.PENDING,
        )
        plan.add_node(wp)
    for wp in plan.nodes.values():
        if any(dep not in plan.nodes for dep in wp.depends_on):
            raise ValueError(f"Unknown dependency in {wp.id}")
    plan.topological_order()
    plan.get_ready_nodes()
    return plan


def run_plan(goal: str, memory_dir: Optional[str] = None) -> bool:
    if not goal or not goal.strip():
        print("[-] /plan komutu için bir hedef belirtmelisin. Örnek: /plan kullanıcı girişi ekle")
        return False

    memory_dir = memory_dir or getattr(
        getattr(settings, "config", None), "memory", None
    )
    if memory_dir is None:
        memory_dir = "Aimemory"
    else:
        memory_dir = getattr(memory_dir, "base_dir", memory_dir) or "Aimemory"

    os.makedirs(memory_dir, exist_ok=True)
    mind_map = _load_mind_map(memory_dir)

    user_prompt = f"""Hedef: {goal.strip()}

Proje Zihin Haritası (varsa):
{mind_map[:12000] if mind_map else "(Zihin haritası henüz yok. /scan çalıştırılmamış olabilir.)"}

Yukarıdaki hedef için DAG iş paketlerini JSON olarak üret.
"""

    print(f"[*] Plan oluşturuluyor → Hedef: {goal.strip()}")
    llm = LLMClient()

    try:
        response, stats = llm.generate_with_stats(
            prompt=user_prompt,
            system_prompt=PLAN_SYSTEM_PROMPT,
        )
    except Exception as e:
        logger.error("LLM çağrısı başarısız: %s", e)
        print(f"[-] LLM hatası: {e}")
        return False

    raw = _extract_json(response)
    if not raw:
        print("[-] LLM geçerli JSON döndürmedi. Ham yanıt loglandı.")
        logger.error("JSON parse edilemedi. Yanıt:\n%s", response[:2000])
        debug_path = Path(memory_dir) / "plan_raw_debug.txt"
        debug_path.write_text(response, encoding="utf-8")
        return False

    try:
        dag = _build_dag_from_llm(raw, goal.strip())
    except Exception as e:
        print(f"[-] DAG oluşturulamadı: {e}")
        logger.exception("DAG build hatası")
        return False

    if not dag.nodes:
        print("[-] Hiç iş paketi üretilmedi.")
        return False

    json_path = Path(memory_dir) / "dag_plan.json"
    try:
        json_path.write_text(dag.model_dump_json(indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[-] dag_plan.json yazılamadı: {e}")
        return False

    md_path = Path(memory_dir) / "master_plan.md"
    try:
        md_path.write_text(dag.to_markdown(), encoding="utf-8")
    except Exception as e:
        logger.warning("master_plan.md yazılamadı: %s", e)

    summary = dag.get_status_summary()
    print(f"[+] DAG Plan kaydedildi → {json_path}")
    print(f"    Toplam düğüm : {len(dag.nodes)}")
    print(f"    Ready        : {summary.get('ready', 0)}")
    print(f"    Pending      : {summary.get('pending', 0)}")
    print(f"    Markdown     : {md_path}")

    try:
        order = dag.topological_order()
        print("    Çalışma sırası (topo): " + " → ".join(order[:8]) + (" ..." if len(order) > 8 else ""))
    except ValueError as e:
        print(f"    [!] Uyarı: {e}")

    return True


