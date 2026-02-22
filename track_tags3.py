
with open('/Users/mrosas/Documents/sgpal/templates/base.html', 'r', encoding='utf-8') as f:
    content = f.read()

tags = []

# Find all template tags, handling multi-line
i = 0
n = len(content)
while i < n:
    open_pos = content.find('{%', i)
    if open_pos == -1:
        break
    close_pos = content.find('%}', open_pos)
    if close_pos == -1:
        break
    token = content[open_pos:close_pos+2].strip()
    
    # Get line number
    line_num = content[:open_pos].count('\n') + 1
    
    if token.startswith('{% if') and not token.endswith('endif %}'):
        print(f"Line {line_num}: OPEN  {token}")
        tags.append( (token, line_num) )
    elif token.startswith('{% endif'):
        if not tags:
            print(f"ERROR: Line {line_num}: CLOSE {token} without matching OPEN")
        else:
            opening_token, opening_line = tags.pop()
            print(f"Line {line_num}: CLOSE {token} matches line {opening_line}: {opening_token}")
            
    i = close_pos + 2

print("\n=== Unclosed tags ===\n")
if tags:
    for token, line in tags:
        print(f"ERROR: Line {line}: OPEN {token} not closed")
else:
    print("All tags are properly closed")
