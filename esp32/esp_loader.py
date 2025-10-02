import sys
import os
import re
from subprocess import run
import subprocess
import ast

def remove_docstrings(source):
    """
    Removes all docstrings and comments from a given Python source string.
    """
    docstring_lines = []

    class DocStringCollector(ast.NodeVisitor):
        def visit_Expr(self, node):
            if isinstance(node.value, (ast.Str, ast.Bytes)):
                docstring_lines.append((node.lineno, node.end_lineno))
            self.generic_visit(node)

    collector = DocStringCollector()
    tree = ast.parse(source)
    collector.visit(tree)
    
    lines = source.splitlines()
    new_lines = []
    skip_to_line = -1

    for index, line in enumerate(lines):
        current_line_num = index + 1
        if current_line_num < skip_to_line:
            continue
        for start, end in docstring_lines:
            if start <= current_line_num <= end:
                new_lines.extend([''] * (end - start + 1))
                skip_to_line = end
                break
        else:
            new_lines.append(line)

    return '\n'.join(new_lines)

def remove_comments_and_docstrings(file_path):
    with open(file_path, 'r') as file:
        source = file.read()

    no_docstrings = remove_docstrings(source)

    # Remove inline comments
    no_comments = "\n".join([re.sub(r'#.*$', '', line) for line in no_docstrings.splitlines()])
    
    return no_comments


def process_path(source_path, base_path, relative_path="", device_name='/dev/tty.SLAB_USBtoUART'):
    full_source_path = os.path.join(base_path, relative_path, source_path)

    # If the source path is a directory, recursively process the files and subdirectories
    if os.path.isdir(full_source_path):
        ensure_dir_on_esp32(os.path.join(relative_path, source_path), device_name)  # Ensure directory on ESP32
        for item in os.listdir(full_source_path):
            item_relative_path = os.path.join(relative_path, source_path)
            process_path(item, base_path, item_relative_path, device_name)
        return
        
    # Variable to keep track of the path to use. It will be modified only if the source is a .py file
    path_to_use = full_source_path
    
    # Check if the file is a Python file
    if full_source_path.endswith('.py'):
        temp_file = 'temp.py'
        cleaned_code = remove_comments_and_docstrings(full_source_path)
        with open(temp_file, 'w') as file:
            file.write(cleaned_code)
        path_to_use = temp_file

    # Construct the destination path
    destination_path = os.path.join(relative_path, source_path)
    
    command = f"/Users/giovannichiementin/anaconda3/envs/esp32/bin/ampy --port {device_name} put {path_to_use} /{destination_path}"
    print(f'\ncommand: {command}\n')

    # Execute the command
    #run(command, shell=True)
    #print("\n\nDoes source path exist?", os.path.exists(full_source_path))
    #print("\n\nDoes temp.py exist?", os.path.exists('temp.py'))

    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        print(output.decode())
    except subprocess.CalledProcessError as e:
        print("Command returned an error:", e.returncode)
        print(e.output.decode())
    

    # Remove the temporary file if created
    if path_to_use == 'temp.py':
        os.remove('temp.py')

def ensure_dir_on_esp32(directory, device_name):
    cmd = ["/Users/giovannichiementin/anaconda3/envs/esp32/bin/ampy", "--port", device_name, "mkdir", directory]
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        pass  # This may error if the directory already exists, which is fine.



def main():
    if len(sys.argv) < 2:
        print('Usage: python esp_loader.py <source/path/to/filename.ext> [optional_device_name]')
        sys.exit(1)

    source_path = sys.argv[1]
    base_path = os.path.dirname(source_path)
    root_name = os.path.basename(source_path)
    device_name = sys.argv[2] if len(sys.argv) > 2 else '/dev/tty.SLAB_USBtoUART'

    process_path(root_name, base_path, "", device_name)

if __name__ == "__main__":
    main()
