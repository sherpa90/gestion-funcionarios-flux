
with open('/Users/mrosas/Documents/sgpal/templates/base.html', 'r', encoding='utf-8') as f:
    content = f.read()

if_count = content.count('{% if ')
endif_count = content.count('{% endif ')
print(f"Total {% if %}: {if_count}")
print(f"Total {% endif %}: {endif_count}")
print(f"Difference: {if_count - endif_count}")
