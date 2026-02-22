
import subprocess

def test_template_without_static():
    # Read and modify base.html temporarily
    with open('/Users/mrosas/Documents/sgpal/templates/base.html', 'r', encoding='utf-8') as f:
        base_html = f.read()
    
    modified_html = base_html.replace("{% load static %}", "")
    modified_html = modified_html.replace("{% static 'core/vendor/fontawesome/css/all.min.css' %}", "https://example.com/fontawesome.css")
    modified_html = modified_html.replace("{% static 'core/vendor/fontawesome/js/all.min.js' %}", "https://example.com/fontawesome.js")
    
    # Write to temporary file
    temp_path = '/Users/mrosas/Documents/sgpal/temp_base.html'
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write(modified_html)
    
    # Copy to container
    subprocess.run(['docker', 'cp', temp_path, 'sgpal-web-1:/app/temp_base.html'], check=True)
    
    # Test in container
    result = subprocess.run([
        'docker', 'exec', 'sgpal-web-1', 
        'python', 'manage.py', 'shell', '-c', 
        "from django.template import Engine; from django.template import TemplateSyntaxError; try: f = open('/app/temp_base.html', 'r', encoding='utf-8'); t = Engine.get_default().from_string(f.read()); print('✓ Template syntax is valid'); except TemplateSyntaxError as e: print('✗ TemplateSyntaxError:', e); import traceback; traceback.print_exc()"
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    # Cleanup
    subprocess.run(['rm', temp_path], check=True)
    subprocess.run(['docker', 'exec', 'sgpal-web-1', 'rm', '/app/temp_base.html'], check=True)
    
    return result.returncode == 0

if __name__ == "__main__":
    print("Testing base.html without static references...")
    test_template_without_static()
