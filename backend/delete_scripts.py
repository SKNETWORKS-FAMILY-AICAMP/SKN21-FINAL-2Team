import os

files_to_delete = [
    "tmp_check_all_keys.py",
    "tmp_check_qdrant.py",
    "tmp_check_qdrant_subcat.py",
    "tmp_check_restaurants.py",
    "tmp_check_specifics.py",
    "tmp_check_vectordb.py",
    "verify_apis.py"
]

base_path = r"c:\Users\Playdata\Documents\SKN21\SKN21-FINAL-2Team\backend"

for file in files_to_delete:
    full_path = os.path.join(base_path, file)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
            print(f"Deleted: {file}")
        except Exception as e:
            print(f"Failed to delete {file}: {e}")
    else:
        print(f"Not found: {file}")
