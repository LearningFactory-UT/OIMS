import os

def recursive_delete(path='/'):
    try:
        for file_or_folder in os.listdir(path):
            item_path = "{}/{}".format(path, file_or_folder)
            if file_or_folder != 'boot.py' or path != '/': # Don't delete /boot.py
                if os.stat(item_path)[0] == 0x4000: # If the item is a directory
                    recursive_delete(item_path)
                    os.rmdir(item_path)
                else: # If the item is a file
                    os.remove(item_path)
    except OSError:
        pass

recursive_delete()
