import os

# Папки, которые мы игнорируем
EXCLUDE = {'.git', '.idea', 'venv', '.venv', 'env', '__pycache__'}


def print_tree(startpath):
    for root, dirs, files in os.walk(startpath):
        # Убираем мусорные папки из обхода
        dirs[:] = [d for d in dirs if d not in EXCLUDE]

        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}📂 {os.path.basename(root) or startpath}/")

        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print(f"{subindent}📄 {f}")


print_tree('.')