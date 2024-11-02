import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
from flask import Flask, render_template_string
from webdriver_manager.chrome import ChromeDriverManager
import json

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KennyUPullScraper:
    def __init__(self, location):
        self.location = location
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/google-chrome")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        self.driver = webdriver.Chrome(
            service=Service(),
            options=chrome_options
        )
        
        self.urls = {
            'Ottawa': "https://kennyupull.com/auto-parts/our-inventory/?branch%5B%5D=1457192&nb_items=42&sort=date",
            'Gatineau': "https://kennyupull.com/auto-parts/our-inventory/?branch%5B%5D=1457182&nb_items=42&sort=date",
            'Cornwall': "https://kennyupull.com/auto-parts/our-inventory/?branch%5B%5D=1576848&nb_items=42&sort=date"
        }

    def handle_cookies(self):
        logger.info("Looking for cookie consent button...")
        time.sleep(5)
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                if "accept" in button.text.lower():
                    button.click()
                    logger.info("Clicked accept cookies button")
                    time.sleep(2)
                    return True
            return False
        except Exception as e:
            logger.error(f"Error handling cookies: {str(e)}")
            return False

    def scroll_to_load(self, pause_time=2):
        logger.info("Scrolling to load more content...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause_time)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def scrape_page(self):
        logger.info(f"Starting scrape for {self.location}...")
        
        try:
            self.driver.get(self.urls[self.location])
            logger.info("Page loaded")
            
            self.handle_cookies()
            self.scroll_to_load(pause_time=3)
            
            logger.info("Waiting for car listings to load...")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "img[data-src]"))
            )
            
            car_elements = self.driver.find_elements(By.CSS_SELECTOR, "img[data-src]")
            logger.info(f"Found {len(car_elements)} potential car listings")
            
            inventory = []
            for car_element in car_elements:
                try:
                    title = car_element.get_attribute("alt")
                    image_url = car_element.get_attribute("data-src")
                    parent_element = car_element.find_element(By.XPATH, "../..")
                    detail_url = parent_element.find_element(By.TAG_NAME, "a").get_attribute("href")
                    
                    try:
                        date_listed = parent_element.find_element(By.CLASS_NAME, "infos--date").text
                    except:
                        date_listed = "N/A"

                    try:
                        row_info = parent_element.find_element(By.XPATH, ".//p[@class='date info']").text
                    except:
                        row_info = "N/A"

                    car = {
                        'title': title,
                        'image_url': image_url,
                        'detail_url': detail_url,
                        'branch': self.location,
                        'date_listed': date_listed,
                        'row': row_info
                    }
                    inventory.append(car)
                    logger.info(f"Added car: {title}")
                    
                except Exception as e:
                    logger.error(f"Error processing car element: {e}")
                    continue

            return inventory
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return []
        finally:
            self.close()

    def close(self):
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass

@app.route('/')
def home():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Kenny U-Pull Inventory Viewer</title>
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
                text-decoration: none;
                transition: background-color 0.3s;
            }
            .button:hover { background-color: #0056b3; }
            .loading { display: none; margin-top: 20px; }
            @media (max-width: 600px) { .button { width: 100%; } }
        </style>
        <script>
            function showLoading(location) {
                document.getElementById('loading').style.display = 'block';
                return true;
            }
        </script>
    </head>
    <body>
        <div class="container">
            <h1 style="color: #007bff;">Kenny U-Pull Inventory Viewer</h1>
            <div class="button-container">
                <a href="/scrape/Ottawa" class="button" onclick="return showLoading('Ottawa')">View Ottawa</a>
                <a href="/scrape/Gatineau" class="button" onclick="return showLoading('Gatineau')">View Gatineau</a>
                <a href="/scrape/Cornwall" class="button" onclick="return showLoading('Cornwall')">View Cornwall</a>
            </div>
            <div id="loading" class="loading">
                Loading inventory... Please wait...
            </div>
        </div>
    </body>
    </html>
    """)

@app.route('/scrape/<location>')
def scrape(location):
    logger.info(f"Received request for {location}")
    scraper = KennyUPullScraper(location)
    inventory = scraper.scrape_page()
    
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
            .card h3 { margin: 10px 0; color: #333; }
            .card p { margin: 5px 0; color: #666; }
            .back-link {
                display: inline-block;
                padding: 10px 20px;
                background-color: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px;
            }
            .back-link:hover { background-color: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="color: #007bff; text-align: center;">{{ location }} Inventory</h1>
            <div class="grid">
            {% for car in inventory %}
                <div class="card">
                    <img src="{{ car['image_url'] }}" alt="{{ car['title'] }}" onerror="this.src='https://via.placeholder.com/150'">
                    <h3>{{ car['title'] }}</h3>
                    <p><strong>Branch:</strong> {{ car['branch'] }}</p>
                    <p><strong>Date Listed:</strong> {{ car['date_listed'] }}</p>
                    <p><strong>Row:</strong> {{ car['row'] }}</p>
                    {% if car['detail_url'] != '#' %}
                    <p><a href="{{ car['detail_url'] }}" target="_blank" style="color: #007bff;">View Details</a></p>
                    {% endif %}
                </div>
            {% endfor %}
            </div>
            <div style="text-align: center;">
                <a href="/" class="back-link">Back to Home</a>
            </div>
        </div>
    </body>
    </html>
    """, location=location, inventory=inventory)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
