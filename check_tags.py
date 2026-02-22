
def check_tag_balance(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    tags = []
    lines = content.split('\n')
    
    print("Checking tag balance in:", file_path)
    print("=" * 80)
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        
        if "{% if " in line or "{% elif " in line or "{% else " in line or "{% endif " in line:
            if "{% if " in line:
                tags.append(("if", line_num))
            elif "{% elif " in line:
                if not tags or tags[-1][0] != "if":
                    print(f"ERROR on line {line_num}: 'elif' without matching 'if'")
            elif "{% else " in line:
                if not tags or tags[-1][0] != "if":
                    print(f"ERROR on line {line_num}: 'else' without matching 'if'")
            elif "{% endif " in line:
                if not tags:
                    print(f"ERROR on line {line_num}: 'endif' without matching 'if'")
                else:
                    open_tag = tags.pop()
                    print(f"Line {line_num}: endif matches line {open_tag[1]}")
    
    if tags:
        for tag in tags:
            print(f"ERROR: Unclosed tag on line {tag[1]}")
    else:
        print("All tags are properly closed")
    
    print(f"\nTotal open tags: {len(tags)}")

check_tag_balance('/Users/mrosas/Documents/sgpal/templates/base.html')
