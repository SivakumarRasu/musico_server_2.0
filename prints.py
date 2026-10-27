# import os

# IGNORE = {".git", "venv", "__pycache__", ".idea"}

# def print_tree(path, prefix=""):
#     items = sorted([i for i in os.listdir(path) if i not in IGNORE])

#     for index, item in enumerate(items):
#         item_path = os.path.join(path, item)
#         is_last = index == len(items) - 1

#         connector = "└── " if is_last else "├── "
#         print(prefix + connector + item)

#         if os.path.isdir(item_path):
#             extension = "    " if is_last else "│   "
#             print_tree(item_path, prefix + extension)

# print(".")
# print_tree(".")

import socket

try:
    socket.create_connection(("smtp.gmail.com", 587), timeout=10)
    print("Connected")
except Exception as e:
    print(e)