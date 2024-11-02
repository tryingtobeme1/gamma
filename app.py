# app.py
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request, Response
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import chromedriver_autoinstaller

# Install ChromeDriver
chromedriver_autoinstaller.install()

# Existing Kenny U-Pull Scraper Code
class KennyUPullScraper:
    def __init__(self, location):
        self.location = location
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")

        self.driver = webdriver.Chrome(
            options=chrome_options
        )

        self.urls = {
            'Ottawa': "https://kennyupull.com/auto-parts/our-inventory/?branch%5B%5D=1457192&nb_items=42&sort=date",
            'Gatineau': "https://kennyupull.com/auto-parts/our-inventory/?branch%5B%5D=1457182&nb_items=42&sort=date",
            'Cornwall': "https://kennyupull.com/auto-parts/our-inventory/?branch%5B%5D=1576848&nb_items=42&sort=date"
        }

    def scrape_page(self):
        ebay_scraper = EbayScraper(None, None, None, 120, 600)
        self.driver.get(self.urls[self.location])
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "img[data-src]"))
        )
        car_elements = self.driver.find_elements(By.CSS_SELECTOR, "img[data-src]")
        inventory = []
        ebay_listings = ebay_scraper.fetch_ebay_listings()
        for car_element in car_elements:
            try:
                title = car_element.get_attribute("alt")
                image_url = car_element.get_attribute("data-src")
                parent_element = car_element.find_element(By.XPATH, "../..")
                try:
                    detail_url = parent_element.find_element(By.TAG_NAME, "a").get_attribute("href")
                except:
                    detail_url = "N/A"
                year, make, model = self.extract_car_details(title)
                car = {
                    'title': title,
                    'image_url': next((listing['Image'] for listing in ebay_listings if listing['Title'].lower().startswith(f"{year} {make} {model}".lower())), image_url),
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

    def extract_car_details(self, title):
        parts = title.split()
        year = parts[0] if parts else "Unknown"
        make = parts[1] if len(parts) > 1 else "Unknown"
        model = parts[2] if len(parts) > 2 else "Unknown"
        return year, make, model

    def close(self):
        if self.driver:
            self.driver.quit()

# eBay Scraper Code (Same as before)
class EbayScraper:
    def __init__(self, year, make, model, min_price, max_price, filter_keyword=None):
        self.year = year
        self.make = make
        self.model = model
        self.min_price = min_price
        self.max_price = max_price
        self.filter_keyword = filter_keyword
        self.listings = []

    def fetch_ebay_listings(self):
        if self.year and self.make and self.model:
            search_term = quote_plus(f"{self.year} {self.make} {self.model}")
        else:
            search_term = quote_plus("MAZDA MAZDA6 2011")
        base_url = "https://www.ebay.com/sch/i.html"
        search_term = quote_plus(f"{self.year} {self.make} {self.model} parts")
        params = {
            '_from': 'R40',
            '_nkw': search_term,
            '_sacat': '0',
            '_udlo': '120',
            '_udhi': '600',
            'LH_Complete': '1',
            'LH_Sold': '1',
            'rt': 'nc',
            '_oaa': '1',
            '_dcat': '6030',
            'LH_ItemCondition': '3000'
        }
        url = f"{base_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/html',
            'Accept-Language': 'en-US',
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.select('li.s-item')
            for item in items:
                title_elem = item.select_one('.s-item__title')
                price_elem = item.select_one('.s-item__price')
                link_elem = item.select_one('a.s-item__link')
                image_elem = item.select_one('img.s-item__image-img')
                image_url = image_elem.get('src') if image_elem and image_elem.has_attr('src') else (image_elem.get('data-src') if image_elem and image_elem.has_attr('data-src') else 'https://via.placeholder.com/150')
                title = title_elem.text.strip() if title_elem else 'No Title Available'
                price = price_elem.text.strip() if price_elem else 'No Price Available'
                link = link_elem['href'] if link_elem else 'N/A'
                
                if self.filter_keyword and title.lower() in self.filter_keyword.lower():
                    continue
                
                self.listings.append({
                    'Title': title,
                    'Price': price,
                    'Link': link,
                    'Image': image_url
                })
        except Exception as e:
            print(f"Error fetching eBay listings: {e}")
            return []
        return self.listings

# Flask App
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
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f0f2f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                text-align: center;
            }
            .button-container {
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 20px;
                margin-top: 30px;
            }
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
            .button:hover {
                background-color: #0056b3;
            }
            @media (max-width: 600px) {
                .button {
                    width: 100%;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="color: #007bff;">Kenny U-Pull Inventory Scraper</h1>
            <div class="button-container">
                <button class="button" onclick="window.location.href='/scrape/Ottawa'">Scrape Ottawa</button>
                <button class="button" onclick="window.location.href='/scrape/Gatineau'">Scrape Gatineau</button>
                <button class="button" onclick="window.location.href='/scrape/Cornwall'">Scrape Cornwall</button>
            </div>
        </div>
    </body>
    </html>
    """)

@app.route('/scrape/<location>')
def scrape(location):
    scraper = KennyUPullScraper(location)
    try:
        inventory = scraper.scrape_page()
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ location }} Inventory - Kenny U-Pull</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f0f2f5;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                }
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
                .card h3 {
                    margin: 10px 0;
                }
                .card a {
                    text-decoration: none;
                    color: #007bff;
                }
                .button {
                    padding: 10px 20px;
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    margin-top: auto;
                    text-align: center;
                    text-decoration: none;
                    display: inline-block;
                }
                .button:hover {
                    background-color: #218838;
                }
                .back-link {
                    display: block;
                    text-align: center;
                    margin-top: 20px;
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
                        <a href="/ebay/{{ car['year'] }}/{{ car['make'] }}/{{ car['model'] }}/120/600" class="button">Search eBay for Parts</a>
                    </div>
                {% endfor %}
                </div>
                <a href="/" class="back-link">Back to Home</a>
            </div>
        </body>
        </html>
        """, location=location, inventory=inventory)
    finally:
        scraper.close()

@app.route('/ebay/<year>/<make>/<model>/<min_price>/<max_price>')
def ebay_search(year, make, model, min_price, max_price):
    ebay_scraper = EbayScraper(year, make, model, min_price, max_price)
    listings = ebay_scraper.fetch_ebay_listings()
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>eBay Listings - {{ year }} {{ make }} {{ model }}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f0f2f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
                background-color: white;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            }
            th, td {
                border: 1px solid #ddd;
                padding: 12px;
                text-align: left;
            }
            th {
                background-color: #007bff;
                color: white;
                cursor: pointer;
            }
            tr:nth-child(even) {
                background-color: #f8f9fa;
            }
            img {
                width: 100px;
                height: auto;
                border-radius: 5px;
            }
            .back-link {
                display: block;
                text-align: center;
                margin-top: 20px;
                color: #007bff;
                text-decoration: none;
            }
            @media (max-width: 600px) {
                table {
                    display: block;
                    overflow-x: auto;
                }
            }
        </style>
    </head>
    <body>
        <div class="container
