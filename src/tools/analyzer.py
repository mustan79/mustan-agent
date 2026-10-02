import os
import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Any

class CodeVisitor(ast.NodeVisitor):
    """Her bir .py dosyasının AST ağacını gezen ziyaretçi sınıfı."""
    def __init__(self):
        self.imports = []
        self.classes = []
        self.functions = []
        self.calls = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.classes.append(node.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.append(node.func.attr)
        self.generic_visit(node)

class ProjectAnalyzer:
    @staticmethod
    def extract_file_skeleton(file_path: str) -> str:
        """Return a compact AST skeleton for prompts and quick inspection."""
        source = Path(file_path).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=file_path)
        lines = []
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                lines.append(ast.unparse(node))
            elif isinstance(node, ast.ClassDef):
                lines.append(f"class {node.name}:")
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args = [a.arg for a in child.args.args]
                        prefix = "async def" if isinstance(child, ast.AsyncFunctionDef) else "def"
                        ret = f" -> {ast.unparse(child.returns)}" if child.returns else ""
                        lines.append(f"    {prefix} {child.name}({', '.join(args)}){ret}:")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in node.args.args]
                prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
                lines.append(f"{prefix} {node.name}({', '.join(args)}){ret}:")
        return "\n".join(lines)

    @staticmethod
    def scan_directory(target_dir: str, memory_dir: str = "Aimemory") -> None:
        target_path = Path(target_dir).resolve()
       
        # Taranmayacak, LLM'in token bütçesini boşa harcamaması gereken yoksayılan dizinler
        ignore_dirs = {
            ".git", "__pycache__", "node_modules", "venv", "env", ".venv", 
            "Aimemory", ".idea", ".vscode", "dist", "build"
        }
        
        analysis_data = {
            "files": {},
            "import_graph": {},
            "call_graph": {},
            "unused_candidates": {
                "files": [],
                "functions": []
            }
        }

        all_defined_functions = set()
        all_called_functions = set()
        all_imported_modules = set()
        all_modules = set()

        # 1. Aşama: Tüm .py dosyalarını bul ve AST ile ayrıştır
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    rel_path = str(file_path.relative_to(target_path))
                    module_name = rel_path.replace(os.sep, ".")[:-3] # Örn: tools.analyzer
                    
                    all_modules.add(module_name)
                    
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            code = f.read()
                        
                        tree = ast.parse(code, filename=str(file_path))
                        visitor = CodeVisitor()
                        visitor.visit(tree)
                        
                        # Graph ve dosya bilgilerini kaydet
                        analysis_data["files"][rel_path] = {
                            "imports": list(set(visitor.imports)),
                            "classes": list(set(visitor.classes)),
                            "functions": list(set(visitor.functions)),
                            "calls": list(set(visitor.calls))
                        }
                        
                        analysis_data["import_graph"][module_name] = list(set(visitor.imports))
                        analysis_data["call_graph"][rel_path] = list(set(visitor.calls))
                        
                        # Kullanılmayan tespiti için kümeleri güncelle
                        all_defined_functions.update(visitor.functions)
                        all_called_functions.update(visitor.calls)
                        all_imported_modules.update(visitor.imports)
                        
                    except SyntaxError:
                        print(f"[-] Syntax Error atlanıyor: {rel_path}")
                    except Exception as e:
                        print(f"[-] Hata okuma ({rel_path}): {e}")

        # 2. Aşama: Kullanılmayan Adayları Belirle (Statik Analiz)
        # Giriş noktalarını (entry points) ve dunder (magic) metotları yoksay
        ignore_funcs = {"__init__", "__main__", "__str__", "__repr__", "__call__", "main"}
        ignore_files = {"__init__", "main", "app", "manage"}

        # Kullanılmayan Fonksiyonlar: Tanımlanmış ama hiçbir yerde çağrılmamış
        unused_funcs = all_defined_functions - all_called_functions - ignore_funcs
        analysis_data["unused_candidates"]["functions"] = list(unused_funcs)

        # Kullanılmayan Dosyalar: Proje içindeki modüllerden hiç import edilmemiş olanlar
        for mod in all_modules:
            mod_basename = mod.split(".")[-1]
            if mod_basename not in ignore_files:
                # Modül adı hiçbir import listesinde geçmiyorsa
                is_imported = any(mod in imp or mod_basename in imp for imp in all_imported_modules)
                if not is_imported:
                    analysis_data["unused_candidates"]["files"].append(mod)

        # 3. Aşama: JSON ve TXT olarak dışa aktar
        ProjectAnalyzer._export_results(analysis_data, memory_dir)

    @staticmethod
    def _export_results(data: dict, memory_dir: str):
        mem_path = Path(memory_dir)
        os.makedirs(mem_path, exist_ok=True)
        
        json_path = mem_path / "proje_mind.json"
        txt_path = mem_path / "proje_mind.md"

        # JSON Çıktısı
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        # TXT/Markdown Çıktısı
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("=== PROJE ANALİZ RAPORU ===\n\n")
            
            f.write("1. DOSYA BİLEŞENLERİ (AST)\n")
            f.write("-" * 40 + "\n")
            for filepath, details in data["files"].items():
                f.write(f"Dosya: {filepath}\n")
                f.write(f"  - Importlar: {', '.join(details['imports']) or 'Yok'}\n")
                f.write(f"  - Sınıflar : {', '.join(details['classes']) or 'Yok'}\n")
                f.write(f"  - Metotlar : {', '.join(details['functions']) or 'Yok'}\n")
                f.write(f"  - Çağrılar : {', '.join(details['calls']) or 'Yok'}\n\n")
            
            f.write("2. KULLANILMAYAN ADAYLAR (Statik Analiz)\n")
            f.write("-" * 40 + "\n")
            f.write(f"Öksüz Dosya/Modül Adayları:\n")
            for uf in data["unused_candidates"]["files"]:
                f.write(f"  - {uf}\n")
            if not data["unused_candidates"]["files"]:
                 f.write("  - Bulunamadı.\n")
                 
            f.write(f"\nÖksüz Fonksiyon Adayları:\n")
            for func in data["unused_candidates"]["functions"]:
                f.write(f"  - {func}()\n")
            if not data["unused_candidates"]["functions"]:
                 f.write("  - Bulunamadı.\n")


