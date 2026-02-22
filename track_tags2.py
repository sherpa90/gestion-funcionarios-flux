
with open('/Users/mrosas/Documents/sgpal/templates/base.html', 'r', encoding='utf-8') as f:
    content = f.read()

tags = []
lines = content.split('\n')

print("=== Tracking tags ===\n")

for i, line in enumerate(lines, 1):
    if '{%' in line:
        tokens = []
        j = 0
        while True:
            open_pos = line.find('{%', j)
            if open_pos == -1:
                break
            close_pos = line.find('%}', open_pos)
            if close_pos == -1:
                break
            token = line[open_pos:close_pos+2].strip()
            if token:
                tokens.append(token)
            j = close_pos + 2
        
        for token in tokens:
            if token.startswith('{% if') and not token.endswith('endif %}'):
                print(f"Line {i}: OPEN  {token}")
                tags.append( (token, i) )
            elif token.startswith('{% endif'):
                if not tags:
                    print(f"ERROR: Line {i}: CLOSE {token} without matching OPEN")
                else:
                    opening_token, opening_line = tags.pop()
                    print(f"Line {i}: CLOSE {token} matches line {opening_line}: {opening_token}")

print("\n=== Unclosed tags ===\n")
if tags:
    for token, line in tags:
        print(f"ERROR: Line {line}: OPEN {token} not closed")
else:
    print("All tags are properly closed")
