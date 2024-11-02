import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from flask import Flask, render_template_string
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import chromedriver_autoinstaller
from selenium.webdriver.chrome.service import Service

# Configure Chrome options for Render deployment
def get_chrome_options():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--remote-debugging-port=9222')
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/google-chrome")
    return chrome_options

class KennyUPullScraper:
    def __init__(self, location):
        self.location = location
        try:
            chromedriver_autoinstaller.install()
            self.driver = webdriver.Chrome(options=get_chrome_options())
        except Exception as e:
            print(f"Error initializing Chrome driver: {e}")
            # Fallback to basic service if automatic installation fails
            service = Service()
            self.driver = webdriver.Chrome(service=service, options=get_chrome_options())

        self.urls = {
            'Ottawa': "https://kennyupull.com/auto-parts/our-inventory/?branch%5B%5D=1457192&nb_items=42&sort=date",
            'Gatineau': "https://kennyupull.com/auto-parts/our-inventory/?branch%5B%5D=1457182&nb_items=42&sort=date",
            'Cornwall': "https://kennyupull.com/auto-parts/our-inventory/?branch%5B%5D=1576848&nb_items=42&sort=date"
        }

    def scrape_page(self):
        try:
            self.driver.get(self.urls[self.location])
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "img[data-src]"))
            )
            car_elements = self.driver.find_elements(By.CSS_SELECTOR, "img[data-src]")
            inventory = []
            
            for car_element in car_elements:
                try:
                    title = car_element.get_attribute("alt")
                    image_url = car_element.get_attribute("data-src")
                    parent_element = car_element.find_element(By.XPATH, "../..")
                    detail_url = parent_element.find_element(By.TAG_NAME, "a").get_attribute("href")
                    
                    year, make, model = self.extract_car_details(title)
                    car = {
                        'title': title,
                        'image_url': image_url,
                        'detail_url': detail_url,
                        'branch': self.location,
                        'year': year,
                        'make': make,
                        'model': model
                    }
                    inventory.append(car)
                except Exception as e:
                    print(f"Error processing car element: {e}")
                    continue
            return inventory
        except Exception as e:
            print(f"Error in scrape_page: {e}")
            return []
        finally:
            try:
                self.close()
            except:
                pass

    def extract_car_details(self, title):
        parts = title.split()
        year = parts[0] if parts else "Unknown"
        make = parts[1] if len(parts) > 1 else "Unknown"
        model = parts[2] if len(parts) > 2 else "Unknown"
        return year, make, model

    def close(self):
        if self.driver:
            self.driver.quit()

class EbayScraper:
    def __init__(self, year, make, model, min_price, max_price):
        self.year = year
        self.make = make
        self.model = model
        self.min_price = min_price
        self.max_price = max_price

    def fetch_ebay_listings(self):
        try:
            search_term = quote_plus(f"{self.year or '2011'} {self.make or 'MAZDA'} {self.model or 'MAZDA6'} parts")
            base_url = "https://www.ebay.com/sch/i.html"
            params = {
                '_nkw': search_term,
                '_sacat': '0',
                '_udlo': self.min_price,
                '_udhi': self.max_price,
            }
            url = f"{base_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            listings = []
            items = soup.select('li.s-item')
            
            for item in items[:10]:  # Limit to first 10 items for faster response
                title = item.select_one('.s-item__title')
                price = item.select_one('.s-item__price')
                link = item.select_one('a.s-item__link')
                image = item.select_one('img.s-item__image-img')
                
                listings.append({
                    'Title': title.text if title else 'No Title',
                    'Price': price.text if price else 'No Price',
                    'Link': link['href'] if link else '#',
                    'Image': image['src'] if image else 'https://via.placeholder.com/150'
                })
            
            return listings
        except Exception as e:
            print(f"Error fetching eBay listings: {e}")
            return []

app = Flask(__name__)

@app.route('/')
def home():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Kenny U-Pull Inventory Scraper</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f0f2f5; }
            .container { max-width: 1200px; margin: 0 auto; text-align: center; }
            .button-container { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-top: 30px; }
            .button {
                padding: 15px 30px;
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                transition: background-color 0.3s;
            }
            .button:hover { background-color: #0056b3; }
            @media (max-width: 600px) { .button { width: 100%; } }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="color: #007bff;">Kenny U-Pull Inventory Scraper</h1>
            <div class="button-container">
                <a href="/scrape/Ottawa" class="button">Scrape Ottawa</a>
                <a href="/scrape/Gatineau" class="button">Scrape Gatineau</a>
                <a href="/scrape/Cornwall" class="button">Scrape Cornwall</a>
            </div>
        </div>
    </body>
    </html>
    """)

@app.route('/scrape/<location>')
def scrape(location):
    try:
        scraper = KennyUPullScraper(location)
        inventory = scraper.scrape_page()
        
        if not inventory:
            return "No inventory found or error occurred", 500
            
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ location }} Inventory - Kenny U-Pull</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f0f2f5; }
                .container { max-width: 1200px; margin: 0 auto; }
                .grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                    gap: 20px;
                    padding: 20px;
                }
                .card {
                    background: white;
                    padding: 15px;
                    border-radius: 10px;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    display: flex;
                    flex-direction: column;
                }
                .card img {
                    width: 100%;
                    height: 200px;
                    object-fit: cover;
                    border-radius: 10px;
                }
                .back-link {
                    display: block;
                    text-align: center;
                    margin: 20px;
                    color: #007bff;
                    text-decoration: none;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 style="color: #007bff; text-align: center;">{{ location }} Inventory</h1>
                <div class="grid">
                {% for car in inventory %}
                    <div class="card">
                        <img src="{{ car['image_url'] }}" alt="{{ car['title'] }}" onerror="this.src='https://via.placeholder.com/150'">
                        <h3><a href="{{ car['detail_url'] }}" target="_blank">{{ car['title'] }}</a></h3>
                        <p>Branch: {{ car['branch'] }}</p>
                    </div>
                {% endfor %}
                </div>
                <a href="/" class="back-link">Back to Home</a>
            </div>
        </body>
        </html>
        """, location=location, inventory=inventory)
    except Exception as e:
        return f"An error occurred: {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
