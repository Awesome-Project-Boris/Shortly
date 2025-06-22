#!/usr/bin/env python3
"""
Script to list all Python (.py) files in a given directory
and save the filenames into a CSV file named py_list.csv.
Usage:
    python3 list_py_files.py /path/to/folder
"""
import argparse
import sys
import csv
from pathlib import Path

def list_python_files(directory: Path):
    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist.", file=sys.stderr)
        sys.exit(1)
    if not directory.is_dir():
        print(f"Error: '{directory}' is not a directory.", file=sys.stderr)
        sys.exit(1)
    # List non-recursive Python files
    return [p.name for p in directory.glob('*.py') if p.is_file()]

def save_to_csv(file_names, output_path: Path):
    try:
        with output_path.open('w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['filename'])
            for name in file_names:
                writer.writerow([name])
        print(f"CSV saved to {output_path}")
    except Exception as e:
        print(f"Error writing CSV: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="List all .py files in a directory and save as py_list.csv."
    )
    parser.add_argument(
        'directory',
        type=Path,
        help='Path to the folder to scan for .py files'
    )
    args = parser.parse_args()

    files = list_python_files(args.directory)
    # Save CSV in the current working directory
    output_csv = Path.cwd() / 'py_list.csv'
    save_to_csv(files, output_csv)

if __name__ == '__main__':
    main()