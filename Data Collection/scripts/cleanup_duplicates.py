import os
import re

def cleanup_duplicates(root_dir):
    print(f"Starting cleanup in: {root_dir}")
    deleted_count = 0
    
    # Pattern to match filenames like "Dec 6_1.json", "Dec 6_2.json", etc.
    # or "Dec 12_Jahki Deloach_1.json" if such patterns exist.
    # We look for a suffix like _N.json where N is a number.
    duplicate_pattern = re.compile(r'^(.*)_(\d+)\.json$')

    for root, dirs, files in os.walk(root_dir):
        for filename in files:
            match = duplicate_pattern.match(filename)
            if match:
                base_name = match.group(1)
                original_filename = f"{base_name}.json"
                
                original_path = os.path.join(root, original_filename)
                duplicate_path = os.path.join(root, filename)
                
                # Check if the original file exists
                if os.path.exists(original_path):
                    try:
                        os.remove(duplicate_path)
                        print(f"Deleted duplicate: {duplicate_path}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"Error deleting {duplicate_path}: {e}")
                else:
                    # In some cases, the duplicate might be the ONLY file if naming went wrong.
                    # As per instruction, we only remove if it is "excess results".
                    # For now, we only delete if the base exists.
                    pass

    print(f"\nCleanup complete. Total files deleted: {deleted_count}")

if __name__ == "__main__":
    data_dir = os.path.join("Data Collection", "data")
    if os.path.exists(data_dir):
        cleanup_duplicates(data_dir)
    else:
        print(f"Directory not found: {data_dir}")
