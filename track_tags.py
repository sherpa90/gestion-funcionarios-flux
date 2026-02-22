
with open('/Users/mrosas/Documents/sgpal/templates/base.html', 'r', encoding='utf-8') as f:
    content = f.read()

tags = []
lines = content.split('\n')

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
                tags.append(('if', i))
            elif token.startswith('{% endif'):
                if not tags:
                    print("ERROR: Line %d has {%% endif %%} without matching {%% if %%}" % i)
                else:
                    opening = tags.pop()
                    print("Line %d: {%% endif %%} matches line %d" % (i, opening[1]))

if tags:
    for tag in tags:
        print("ERROR: Line %d has unclosed {%% if %%}" % tag[1])
