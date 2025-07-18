#!/usr/bin/env python3
"""
Test script for the Write File tool functionality.
This script demonstrates how the Write File tool works across different model providers.
"""

import os
import tempfile
import shutil
from main import OllamaChat
import tkinter as tk
from tkinterdnd2 import TkinterDnD

def test_file_write_detection():
    """Test the file write detection functionality."""
    print("Testing Write File tool detection...")
    
    # Create a temporary root for testing
    root = TkinterDnD.Tk()
    root.withdraw()  # Hide the window
    
    try:
        # Create app instance
        app = OllamaChat(root)
        
        # Enable write file tool
        app.write_file_var.set(True)
        
        # Test cases
        test_cases = [
            {
                'name': 'Simple file path',
                'response': 'Here is your summary:\n\n```\nThis is a test summary\n```\n\nPlease save this as [["C:\\temp\\summary.txt"]]',
                'expected_files': 1
            },
            {
                'name': 'Multiple files',
                'response': '''
                Create these files:
                
                First file [["C:\\temp\\file1.txt"]]:
                ```
                Content for file 1
                ```
                
                Second file [["C:\\temp\\file2.md"]]:
                ```markdown
                # Markdown Content
                This is markdown content.
                ```
                ''',
                'expected_files': 2
            },
            {
                'name': 'JSON file',
                'response': '''
                Here's your data as JSON [["C:\\temp\\data.json"]]:
                ```json
                {
                    "name": "Test",
                    "value": 123,
                    "items": ["a", "b", "c"]
                }
                ```
                ''',
                'expected_files': 1
            }
        ]
        
        # Create temp directory for testing
        temp_dir = tempfile.mkdtemp()
        print(f"Using temp directory: {temp_dir}")
        
        for test_case in test_cases:
            print(f"\nTesting: {test_case['name']}")
            
            # Replace C:\temp with our temp directory
            response = test_case['response'].replace('C:\\temp', temp_dir)
            
            # Test detection
            write_requests = app.detect_file_write_requests(response)
            
            print(f"  Detected {len(write_requests)} file write requests")
            print(f"  Expected {test_case['expected_files']} files")
            
            if len(write_requests) == test_case['expected_files']:
                print("  ✅ Detection test PASSED")
                
                # Test actual file writing
                files_written = app.process_file_write_requests(response)
                
                if files_written == test_case['expected_files']:
                    print("  ✅ File writing test PASSED")
                    
                    # Verify files exist and have content
                    for request in write_requests:
                        file_path = request['path'].replace('C:\\temp', temp_dir)
                        if os.path.exists(file_path):
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                print(f"    📄 {os.path.basename(file_path)}: {len(content)} characters")
                        else:
                            print(f"    ❌ File not found: {file_path}")
                else:
                    print(f"  ❌ File writing test FAILED: wrote {files_written}, expected {test_case['expected_files']}")
            else:
                print(f"  ❌ Detection test FAILED: found {len(write_requests)}, expected {test_case['expected_files']}")
        
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"\nCleaned up temp directory: {temp_dir}")
        
        print("\n🎉 Write File tool testing completed!")
        
    finally:
        root.destroy()

def test_path_validation():
    """Test path validation functionality."""
    print("\nTesting path validation...")
    
    root = TkinterDnD.Tk()
    root.withdraw()
    
    try:
        app = OllamaChat(root)
        
        test_paths = [
            ("C:\\valid\\path\\file.txt", True, "Valid Windows path"),
            ("/valid/unix/path/file.txt", True, "Valid Unix path"),
            ("relative/path/file.txt", True, "Valid relative path"),
            ("file.txt", True, "Simple filename"),
            ("", False, "Empty path"),
            ("file_without_extension", False, "No file extension"),
            ("path/with/invalid<char.txt", False, "Invalid character"),
            ("a" * 300 + ".txt", False, "Path too long"),
        ]
        
        for path, expected, description in test_paths:
            result = app.is_valid_file_path(path)
            status = "✅" if result == expected else "❌"
            print(f"  {status} {description}: '{path}' -> {result}")
    
    finally:
        root.destroy()

def demonstrate_usage():
    """Demonstrate how to use the Write File tool."""
    print("\n" + "="*60)
    print("WRITE FILE TOOL - USAGE DEMONSTRATION")
    print("="*60)
    
    print("""
The Write File tool allows the AI to create files directly when you specify paths.

USAGE EXAMPLES:

1. Simple text file:
   "Create a summary and save it as [[\"/path/to/summary.txt\"]]"

2. Code file:
   "Write a Python script and save it as [[\"C:\\scripts\\hello.py\"]]"

3. JSON data:
   "Generate JSON data and save as [[\"./data/config.json\"]]"

4. Multiple files:
   "Create both a README.md as [[\"README.md\"]] and a config file as [[\"config.json\"]]"

SUPPORTED FORMATS:
- Text files: .txt, .md, .csv
- Code files: .py, .js, .html, .css, .xml
- Data files: .json, .yaml, .ini
- And many more!

SAFETY FEATURES:
- Path validation and sanitization
- File size limits (10MB max)
- Automatic backup of existing files
- Directory creation if needed
- Permission checking

The tool works universally across all model providers:
✅ Ollama
✅ Google Gemini  
✅ DeepSeek
✅ Anthropic Claude
""")

if __name__ == "__main__":
    print("Write File Tool - Test Suite")
    print("="*40)
    
    # Run tests
    test_file_write_detection()
    test_path_validation()
    demonstrate_usage()
    
    print("\nAll tests completed! 🚀")
