import requests
from bs4 import BeautifulSoup

r = requests.get("https://example.com", timeout=10)
soup = BeautifulSoup(r.text, "html.parser")
print(r.status_code, soup.title.string)
print("Hello World")