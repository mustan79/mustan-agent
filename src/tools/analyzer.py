### `src/tools/analyzer.py`
import os
import ast
import logging
from pathlib import Path
from typing import List, Optional, Dict

# Loglama ayarı (Uygulama genelindeki loglayıcıyı kullanır)
logger = logging.getLogger("mustan_agent.tools.analyzer")

# Taranmayacak, LLM'in token bütçesini boşa harcamaması gereken yoksayılan dizinler
IGNORED_DIRS = {
    ".git", "__pycache__", "node_modules", "venv", "env", ".venv", 
    "Aimemory", ".idea", ".vscode", "dist", "build"
}

class ASTSkeletonVisitor(ast.NodeVisitor):
    """
    Python dosyasının AST (Soyut Sözdizimi Ağacı) üzerinde gezinerek
    sadece Sınıf (Class), Fonksiyon (Function) ve Import imzalarını çıkaran ziyaretçi sınıf.
    Kodu okurken gövdeyi yutar, sadece iskeleti bırakarak LLM token bütçesini korur.
    """
    def __init__(self):
        self.skeleton_lines: List[str] = []
        self.imports: List[str] = []
        self.current_indent = 0

    def add_line(self, line: str):
        """Mevcut girinti (indent) seviyesine göre satır ekler."""
        indentation = "    " * self.current_indent
        self.skeleton_lines.append(f"{indentation}{line}")

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(f"import {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        names = ", ".join(alias.name for alias in node.names)
        self.imports.append(f"from {module} import {names}")
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        # Sınıf imzasını oluştur (Miras aldığı sınıflarla birlikte)
        bases = ", ".join(b.id for b in node.bases if isinstance(b, ast.Name))
        bases_str = f"({bases})" if bases else ""
        self.add_line(f"class {node.name}{bases_str}:")
        
        # Docstring (Açıklama) varsa ilk satırını al (LLM'e bağlam vermek için)
        docstring = ast.get_docstring(node)
        if docstring:
            first_line = docstring.strip().split('\n')
            self.add_line(f'    """{first_line}"""')
        else:
            self.add_line("    ...")
            
        # Sınıfın içindeki metotları okumak için girintiyi artır
        self.current_indent += 1
        self.generic_visit(node)
        self.current_indent -= 1
        self.add_line("") # Sınıf sonu boşluğu

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_function(node, is_async=True)

    def _handle_function(self, node, is_async=False):
        # Fonksiyon parametrelerini güvenlice çıkar
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")
            
        args_str = ", ".join(args)
        prefix = "async def " if is_async else "def "
        
        # Dönüş tipi (Type Hint) varsa ekle
        returns = ""
        if node.returns and isinstance(node.returns, ast.Name):
            returns = f" -> {node.returns.id}"
            
        self.add_line(f"{prefix}{node.name}({args_str}){returns}:")
        
        # Fonksiyonun ne yaptığını anlatan docstring'i ekle
        docstring = ast.get_docstring(node)
        if docstring:
            first_line = docstring.strip().split('\n')
            self.add_line(f'    """{first_line}"""')
        else:
            self.add_line("    pass")
            
        # İç içe fonksiyonları yakalamak için devam et
        self.current_indent += 1
        self.generic_visit(node)
        self.current_indent -= 1

class ProjectAnalyzer:
    """
    Proje genelinde dosya okuma, AST çıkarma ve 'Zihin Haritası' (Mind Map) 
    oluşturma işlemlerini yürüten ana araç sınıfıdır.
    ExplorerAgent tarafından kullanılır.
    """

    @staticmethod
    def extract_file_skeleton(file_path: str | Path) -> str:
        """
        Belirtilen Python dosyasının sadece sınıflarını, fonksiyonlarını ve import'larını
        okuyarak bir iskelet çıkarır. Hatalı dosyalarda güvenli çıkış yapar.
        """
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return f"[-] Dosya bulunamadı: {path}"

        try:
            with open(path, "r", encoding="utf-8") as f:
                source_code = f.read()
                
            # Boş dosyalar için erken çıkış
            if not source_code.strip():
                return f"### Dosya: {path.name}\n(Boş Dosya)\n"

            # AST Ağacını ayrıştır
            tree = ast.parse(source_code, filename=str(path))
            visitor = ASTSkeletonVisitor()
            visitor.visit(tree)

            # Çıktıyı LLM'in okumayı en sevdiği Markdown formatında birleştir
            result = [f"### Dosya: {path}"]
            if visitor.imports:
                result.append("**İçe Aktarmalar:**")
                result.append("    " + ", ".join(visitor.imports[:5]) + ("..." if len(visitor.imports) > 5 else ""))
                result.append("")
                
            result.append("**İskelet:**")
            result.append("```python")
            result.extend(visitor.skeleton_lines)
            result.append("```")
            result.append("-" * 40)
            
            return "\n".join(result)

        except SyntaxError as e:
            logger.warning(f"Syntax (Yazım) hatası nedeniyle {path.name} iskeleti çıkarılamadı: {str(e)}")
            return f"### Dosya: {path}\n[-] Syntax Error (Kod hatalı): {str(e)}\n"
        except Exception as e:
            logger.error(f"Dosya analizinde beklenmeyen hata ({path}): {str(e)}")
            return f"### Dosya: {path}\n[-] Okuma Hatası: {str(e)}\n"

    @staticmethod
    def scan_directory(target_dir: str = ".") -> str:
        """
        /scan komutunun kalbi: Hedef dizindeki tüm dosyaları yoksayılanları atlayarak
        tarar ve tüm projenin 'Zihin Haritasını' (Mind Map) tek bir Markdown metni olarak döner.
        """
        root_path = Path(target_dir).resolve()
        mind_map: List[str] = [f"# Proje Zihin Haritası (Dizin: {root_path.name})", ""]
        
        if not root_path.exists() or not root_path.is_dir():
            return f"[-] Hedef dizin bulunamadı: {root_path}"

        # Dizini ağaç yapısı olarak gez
        for current_root, dirs, files in os.walk(root_path):
            # Yoksayılacak klasörleri (örneğin node_modules, .git) atla
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            
            curr_dir = Path(current_root)
            
            # Sadece Python kodlarını analiz et
            py_files = [f for f in files if f.endswith(".py")]
            
            if py_files:
                # Dizin başlığı
                rel_path = curr_dir.relative_to(root_path)
                display_path = "." if str(rel_path) == "." else str(rel_path)
                mind_map.append(f"## Dizin: `{display_path}/`")
                
                # Her dosyanın iskeletini haritaya ekle
                for py_file in py_files:
                    file_path = curr_dir / py_file
                    skeleton = ProjectAnalyzer.extract_file_skeleton(file_path)
                    mind_map.append(skeleton)
                    
        if len(mind_map) == 2:
            return mind_map + "\n\n[-] Bu dizinde analiz edilecek Python dosyası bulunamadı."
            
        logger.info(f"Proje taraması tamamlandı: {root_path}")
        return "\n".join(mind_map)


