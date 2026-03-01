import re

with open('/Users/mrosas/Documents/sgpal/templates/base.html', 'r') as f:
    content = f.read()

# Fix all patterns where user.role == is followed by a newline
# Pattern 1: user.role == 'X' or user.role ==\n   '
pattern1 = r"user\.role == '[\w]+' or user\.role ==\n\s+'"
replacement1 = "user.role == '"

content = re.sub(pattern1, replacement1, content)

# Pattern 2: user.role ==\n   '
pattern2 = r"user\.role ==\n\s+'"
replacement2 = "user.role == '"

content = re.sub(pattern2, replacement2, content)

with open('/Users/mrosas/Documents/sgpal/templates/base.html', 'w') as f:
    f.write(content)

print('Fixed multi-line conditions')
