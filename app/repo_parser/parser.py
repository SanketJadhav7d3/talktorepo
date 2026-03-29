
'''
To parse the code
'''
import ast
import hashlib
import os
from tree_sitter import Language, Parser
import tree_sitter_javascript
import tree_sitter_typescript
import tree_sitter_java
import tree_sitter_cpp
import tree_sitter_go
import tree_sitter_rust

class CodeParser:
    def __init__(self):
        # Initialize languages
        self.js_lang = Language(tree_sitter_javascript.language())
        self.ts_lang = Language(tree_sitter_typescript.language_typescript())
        self.java_lang = Language(tree_sitter_java.language())
        self.cpp_lang = Language(tree_sitter_cpp.language())
        self.go_lang = Language(tree_sitter_go.language())
        self.rust_lang = Language(tree_sitter_rust.language())
        self.parser = Parser()

    def parse_file(self, file_path):
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()

        # Generate content hash to detect changes
        source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()

        if ext == ".py":
            result = self._parse_python(source)
        elif ext in [".js", ".ts", ".java", ".cpp", ".hpp", ".h", ".cc", ".cxx", ".go", ".rs"]:
            result = self._parse_with_tree_sitter(source, ext)
        else:
            result = {"functions": [], "classes": [], "imports": [], "source": source}

        result["hash"] = source_hash
        return result

    def _parse_python(self, source):
        source_lines = source.splitlines()
        tree = ast.parse(source)

        functions = []
        classes = []
        imports = []

        # Process top-level functions, classes, and imports
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                start = node.lineno - 1
                end = node.end_lineno
                text = "\n".join(source_lines[start:end])
                functions.append({
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                    "text": text
                })
            elif isinstance(node, ast.ClassDef):
                methods = []
                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        m_start = child.lineno - 1
                        m_end = child.end_lineno
                        m_text = "\n".join(source_lines[m_start:m_end])
                        methods.append({
                            "name": child.name,
                            "start_line": child.lineno,
                            "end_line": child.end_lineno,
                            "text": m_text
                        })
                start = node.lineno - 1
                end = node.end_lineno
                text = "\n".join(source_lines[start:end])
                classes.append({
                    "name": node.name,
                    "methods": methods,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                    "text": text
                })
            elif isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)


        return {
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "source": source
        }

    def _parse_with_tree_sitter(self, source, extension):
        functions = []
        classes = []
        imports = []
        
        # Select appropriate language
        if extension in [".js", ".ts"]:
            lang = self.ts_lang if extension == ".ts" else self.js_lang
        elif extension == ".java":
            lang = self.java_lang
        elif extension in [".cpp", ".hpp", ".h", ".cc", ".cxx"]:
            lang = self.cpp_lang
        elif extension == ".go":
            lang = self.go_lang
        elif extension == ".rs":
            lang = self.rust_lang
        else:
            return {"functions": [], "classes": [], "imports": [], "source": source}

        self.parser.language = lang
        
        tree = self.parser.parse(bytes(source, "utf8"))
        root_node = tree.root_node

        def traverse(node):
            # 1. Extract Imports / Includes
            if node.type in ["import_statement", "import_declaration", "use_declaration", "import_spec"]:
                src_node = node.child_by_field_name("source") or node.child_by_field_name("path")
                if src_node: # JS/TS
                    imports.append(src_node.text.decode("utf8").strip("'\""))
                elif node.type == "use_declaration": # Rust
                    imports.append(node.text.decode("utf8").replace("use ", "").strip("; "))
                else: # Java
                    text = node.text.decode("utf8")
                    if text.startswith("import "):
                        imports.append(text.replace("import ", "").strip("; "))
            
            elif node.type == "preproc_include": # C++
                path_node = node.child_by_field_name("path")
                if path_node:
                    imports.append(path_node.text.decode("utf8").strip("<>\""))

            elif node.type == "call_expression":
                function_node = node.child_by_field_name("function")
                if function_node and function_node.text.decode("utf8") == "require":
                    args = node.child_by_field_name("arguments")
                    if args and len(args.children) > 1:
                        path_node = args.children[1]
                        imports.append(path_node.text.decode("utf8").strip("'\""))

            # 2. Extract Classes / Structs
            elif node.type in ["class_declaration", "class_specifier", "struct_specifier", "struct_item", "type_declaration", "impl_item"]:
                name_node = node.child_by_field_name("name") or node.child_by_field_name("type")
                
                # Go: type MyStruct struct {}
                if not name_node and node.type == "type_declaration":
                    for child in node.children:
                        if child.type == "type_spec":
                            name_node = child.child_by_field_name("name")
                            break

                name = name_node.text.decode("utf8") if name_node else "Anonymous"
                
                methods = []
                body = node.child_by_field_name("body") or node.child_by_field_name("members") or node
                if body:
                    for child in body.children:
                        if child.type in ["method_definition", "method_declaration", "function_definition", "function_item"]:
                            m_name_node = child.child_by_field_name("name") or child.child_by_field_name("declarator")
                            methods.append({
                                "name": m_name_node.text.decode("utf8") if m_name_node else "method",
                                "start_line": child.start_point[0] + 1,
                                "end_line": child.end_point[0] + 1,
                                "text": child.text.decode("utf8")
                            })

                classes.append({
                    "name": name,
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "text": node.text.decode("utf8"),
                    "methods": methods
                })

            # 3. Extract Top-level Functions
            elif node.type in ["function_declaration", "function_definition", "function_item", "method_declaration"]:
                # Only capture if not nested inside a class (which is handled above)
                if not node.parent or node.parent.type in ["translation_unit", "program", "source_file", "compilation_unit", "source_file"]:
                    name_node = node.child_by_field_name("name") or node.child_by_field_name("declarator") or node.child_by_field_name("type")
                    functions.append({
                        "name": name_node.text.decode("utf8") if name_node else "anonymous",
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "text": node.text.decode("utf8")
                    })

            for child in node.children:
                traverse(child)

        traverse(root_node)
        
        return {
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "source": source
        }
