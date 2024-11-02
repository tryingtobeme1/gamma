import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
from datetime import datetime
from webdriver_manager.chrome import ChromeDriverManager
from flask import Flask, render_template_string, jsonify, request, Response
import threading
import queue
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import webbrowser

# Existing Kenny U-Pull Scraper Code
class KennyUPullScraper:
    def __init__(self, location):
        self.location = location
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
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
        # Simple extraction of year, make, and model from title.
        parts = title.split()
        year = parts[0] if parts else "Unknown"
        make = parts[1] if len(parts) > 1 else "Unknown"
        model = parts[2] if len(parts) > 2 else "Unknown"
        return year, make, model

    def close(self):
        if self.driver:
            self.driver.quit()

# eBay Scraper Code
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
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('li.s-item')
        for item in items:
            title_elem = item.select_one('.s-item__title')
            price_elem = item.select_one('.s-item__price')
            link_elem = item.select_one('a.s-item__link')
            image_elem = item.select_one('img.s-item__image-img') if item.select_one('img.s-item__image-img') else None
            image_url = image_elem['src'] if image_elem and image_elem.has_attr('src') else (image_elem['data-src'] if image_elem and image_elem.has_attr('data-src') else 'https://via.placeholder.com/150')
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
        return self.listings

# Flask App Integration
app = Flask(__name__)

@app.route('/')
def home():
    return render_template_string("""
    <div style="text-align: center; font-family: Arial, sans-serif; padding: 50px; background-color: #f0f2f5;">
        <h1 style="color: #007bff;">Kenny U-Pull Inventory Scraper</h1>
        <div style="display: flex; justify-content: center; gap: 20px; margin-top: 30px;">
            <button style="padding: 15px 30px; background-color: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;" onclick="window.location.href='/scrape/Ottawa'">Scrape Ottawa</button>
            <button style="padding: 15px 30px; background-color: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;" onclick="window.location.href='/scrape/Gatineau'">Scrape Gatineau</button>
            <button style="padding: 15px 30px; background-color: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;" onclick="window.location.href='/scrape/Cornwall'">Scrape Cornwall</button>
        </div>
    </div>
    """)

@app.route('/scrape/<location>')
def scrape(location):
    scraper = KennyUPullScraper(location)
    try:
        inventory = scraper.scrape_page()
        return render_template_string("""
        <div style="font-family: Arial, sans-serif; padding: 50px; background-color: #f0f2f5;">
            <h1 style="color: #007bff;">{{ location }} Inventory</h1>
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px;">
            {% for car in inventory %}
                <div style="background: white; padding: 15px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); display: flex; flex-direction: column; justify-content: space-between; height: 100%;">
                    <img src="{{ car['image_url'] }}" alt="{{ car['title'] }}" style="width: 100%; height: auto; border-radius: 10px;">
                    <h3 style="color: #333; margin-top: 10px;"><a href="{{ car['detail_url'] }}" target="_blank" style="text-decoration: none; color: #007bff;">{{ car['title'] }}</a></h3>
                    <p style="color: #666;">Branch: {{ car['branch'] }}</p>
                    <button style="padding: 10px 20px; background-color: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; margin-top: auto; align-self: center;" onclick="window.location.href='/ebay/{{ car['year'] }}/{{ car['make'] }}/{{ car['model'] }}/120/600'">Search eBay for Parts</button>
                </div>
            {% endfor %}
            </div>
            <div style="margin-top: 30px; text-align: center;">
                <a href="/" style="text-decoration: none; color: #007bff;">Back to Home</a>
            </div>
        </div>
        """, location=location, inventory=inventory)
    finally:
        scraper.close()

@app.route('/ebay/<year>/<make>/<model>/<min_price>/<max_price>')
def ebay_search(year, make, model, min_price, max_price):
    ebay_scraper = EbayScraper(year, make, model, min_price, max_price)
    listings = ebay_scraper.fetch_ebay_listings()
    return render_template_string("""
    <div style="font-family: Arial, sans-serif; padding: 50px; background-color: #f0f2f5;">
        <h1 style="color: #007bff;">eBay Listings for {{ year }} {{ make }} {{ model }}</h1>
        <table id="ebay-table" style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <thead>
                <tr>
                    <th style="border: 1px solid #ddd; padding: 8px; cursor: pointer;" onclick="sortTable(0)">Title</th>
                    <th style="border: 1px solid #ddd; padding: 8px; cursor: pointer;" onclick="sortTable(0)">Price</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Image</th>
                    
                </tr>
            </thead>
            <tbody>
            {% for item in listings %}
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;"><a href="{{ item['Link'] }}" target="_blank" style="text-decoration: none; color: #007bff;">{{ item['Title'] }}</a></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{{ item['Price'] }}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;"><img src="{{ item['Image'] }}" alt="{{ item['Title'] }}" style="width: 100px; height: auto;"></td>
                    
                </tr>
            {% endfor %}
            </tbody>
        </table>
        <div style="margin-top: 30px; text-align: center;">
            <a href="/" style="text-decoration: none; color: #007bff;">Back to Home</a>
        </div>
        <script>
            function sortTable(n) {
                var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
                table = document.getElementById("ebay-table");
                switching = true;
                dir = "asc";
                while (switching) {
                    switching = false;
                    rows = table.rows;
                    for (i = 1; i < (rows.length - 1); i++) {
                        shouldSwitch = false;
                        x = rows[i].getElementsByTagName("TD")[n];
                        y = rows[i + 1].getElementsByTagName("TD")[n];
                        if (dir == "asc") {
                            if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {
                                shouldSwitch = true;
                                break;
                            }
                        } else if (dir == "desc") {
                            if (x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase()) {
                                shouldSwitch = true;
                                break;
                            }
                        }
                    }
                    if (shouldSwitch) {
                        rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                        switching = true;
                        switchcount++;
                    } else {
                        if (switchcount == 0 && dir == "asc") {
                            dir = "desc";
                            switching = true;
                        }
                    }
                }
            }
        </script>
    </div>
    """, year=year, make=make, model=model, listings=listings)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=10000)
