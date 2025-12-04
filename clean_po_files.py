#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PO File Cleaner - Removes duplicates and fixes formatting
Usage: python3 clean_po_files.py
"""

import os
import sys
from collections import OrderedDict

def clean_po_file(input_path, output_path):
    """
    Clean .po file by removing:
    - Duplicate msgid entries (keeps first occurrence)
    - EOF markers
    - Invalid syntax
    """
    
    print(f"\n🔧 Processing: {input_path}")
    
    if not os.path.exists(input_path):
        print(f"❌ Error: File not found: {input_path}")
        return False
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False
    
    # Step 1: Remove EOF markers
    lines = content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Skip EOF markers
        if line.strip() in ['EOF', '<<EOF', "<<'EOF'", '<<"EOF"']:
            print(f"   ➜ Removed EOF marker at line")
            continue
        # Skip lines with EOF in shell heredoc syntax
        if '<<' in line and 'EOF' in line:
            print(f"   ➜ Removed heredoc EOF at line")
            continue
        cleaned_lines.append(line)
    
    # Step 2: Parse and remove duplicates
    header = []
    entries = OrderedDict()
    current_entry = []
    current_msgid = None
    in_header = True
    
    for i, line in enumerate(cleaned_lines):
        # Header section (before first real msgid)
        if in_header:
            header.append(line)
            # Header ends after empty msgid block
            if line.startswith('msgstr') and i > 0:
                # Check if this is the header msgstr
                if any('msgid ""' in h for h in header[-5:]):
                    continue
                else:
                    in_header = False
            continue
        
        # Parse message entries
        if line.startswith('msgid '):
            # Save previous entry if exists
            if current_msgid is not None:
                if current_msgid not in entries:
                    entries[current_msgid] = '\n'.join(current_entry)
                else:
                    print(f"   ➜ Removed duplicate: {current_msgid[:50]}...")
            
            # Start new entry
            current_msgid = line
            current_entry = [line]
        
        elif line.startswith('msgstr '):
            current_entry.append(line)
        
        elif line.startswith('#'):
            # Comment line
            current_entry.append(line)
        
        elif line.strip() == '':
            # Empty line (separator)
            current_entry.append(line)
        
        else:
            # Continuation line (quoted strings)
            if line.startswith('"') and current_entry:
                current_entry.append(line)
            else:
                current_entry.append(line)
    
    # Save last entry
    if current_msgid is not None:
        if current_msgid not in entries:
            entries[current_msgid] = '\n'.join(current_entry)
        else:
            print(f"   ➜ Removed duplicate: {current_msgid[:50]}...")
    
    # Step 3: Reconstruct file
    output_content = '\n'.join(header) + '\n'
    
    for msgid, entry_text in entries.items():
        output_content += entry_text + '\n'
    
    # Step 4: Write cleaned file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)
        print(f"✅ Cleaned file saved: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error writing file: {e}")
        return False


def main():
    """Main function to clean all locale files"""
    
    print("=" * 60)
    print("🧹 PO FILE CLEANER - Removing Duplicates & Fixing Format")
    print("=" * 60)
    
    # Define file paths
    locale_dir = "locale"
    
    files_to_clean = [
        (f"{locale_dir}/uz/LC_MESSAGES/django.po", 
         f"{locale_dir}/uz/LC_MESSAGES/django_cleaned.po"),
        
        (f"{locale_dir}/uz_Cyrl/LC_MESSAGES/django.po", 
         f"{locale_dir}/uz_Cyrl/LC_MESSAGES/django_cleaned.po"),
        
        (f"{locale_dir}/ru/LC_MESSAGES/django.po", 
         f"{locale_dir}/ru/LC_MESSAGES/django_cleaned.po"),
    ]
    
    success_count = 0
    
    for input_file, output_file in files_to_clean:
        if clean_po_file(input_file, output_file):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"✅ Cleaned {success_count}/{len(files_to_clean)} files successfully!")
    print("=" * 60)
    
    if success_count == len(files_to_clean):
        print("\n📋 NEXT STEPS:")
        print("1. Backup original files (optional):")
        print(f"   mv {locale_dir}/uz/LC_MESSAGES/django.po {locale_dir}/uz/LC_MESSAGES/django.po.backup")
        print(f"   mv {locale_dir}/uz_Cyrl/LC_MESSAGES/django.po {locale_dir}/uz_Cyrl/LC_MESSAGES/django.po.backup")
        print(f"   mv {locale_dir}/ru/LC_MESSAGES/django.po {locale_dir}/ru/LC_MESSAGES/django.po.backup")
        print("\n2. Replace with cleaned files:")
        print(f"   mv {locale_dir}/uz/LC_MESSAGES/django_cleaned.po {locale_dir}/uz/LC_MESSAGES/django.po")
        print(f"   mv {locale_dir}/uz_Cyrl/LC_MESSAGES/django_cleaned.po {locale_dir}/uz_Cyrl/LC_MESSAGES/django.po")
        print(f"   mv {locale_dir}/ru/LC_MESSAGES/django_cleaned.po {locale_dir}/ru/LC_MESSAGES/django.po")
        print("\n3. Compile messages:")
        print("   msgfmt -o locale/uz/LC_MESSAGES/django.mo locale/uz/LC_MESSAGES/django.po")
        print("   msgfmt -o locale/uz_Cyrl/LC_MESSAGES/django.mo locale/uz_Cyrl/LC_MESSAGES/django.po")
        print("   msgfmt -o locale/ru/LC_MESSAGES/django.mo locale/ru/LC_MESSAGES/django.po")
        print("\n4. Restart server:")
        print("   python manage.py runserver")
    else:
        print("\n⚠️  Some files had errors. Check the output above.")
    
    return success_count == len(files_to_clean)


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)