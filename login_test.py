import requests

# First, get CSRF token
login_url = 'http://localhost:8000/login/'
session = requests.Session()
response = session.get(login_url)

# Extract CSRF token from cookies
csrf_token = session.cookies.get('csrftoken')
print(f"CSRF Token: {csrf_token}")

# Login with credentials
login_data = {
    'username': 'mrosas@losalercespuertomontt.cl',
    'password': 'Mrosas12345!',
    'csrfmiddlewaretoken': csrf_token
}

headers = {
    'Referer': login_url
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
