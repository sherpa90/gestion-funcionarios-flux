import requests
from bs4 import BeautifulSoup

# First, get login page
login_url = 'http://localhost:8000/login/'
session = requests.Session()
response = session.get(login_url)

# Extract CSRF token from form
soup = BeautifulSoup(response.text, 'html.parser')
csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
print(f"CSRF Token: {csrf_token}")

# Login with credentials
login_data = {
    'username': 'mrosas@losalercespuertomontt.cl',
    'password': 'Mrosas12345!',
    'csrfmiddlewaretoken': csrf_token
}

headers = {
    'Referer': login_url,
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36'
}

response = session.post(login_url, data=login_data, headers=headers)

print(f"\nResponse Status Code: {response.status_code}")
print(f"Response Headers: {dict(response.headers)}")

if response.status_code == 200:
    print(f"\nResponse Content: {response.text[:500]}")
elif response.status_code == 302:
    print(f"\nRedirect to: {response.headers.get('Location')}")
    # Follow redirect
    response = session.get(response.headers.get('Location'))
    print(f"\nRedirect Response Status: {response.status_code}")
    print(f"\nRedirect Response Content: {response.text[:500]}")
else:
    print(f"\nError: {response.text}")
