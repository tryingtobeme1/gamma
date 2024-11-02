import os
import requests
from flask import Flask, render_template_string
from bs4 import BeautifulSoup
import json
import time
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_kenny_upull(location):
    urls = {
        'Ottawa': "https://kennyupull.com/auto-parts/our-inventory/?branch%5B%5D=1457192&nb_items=42&sort=date",
        'Gatineau': "https://kennyupull.com/auto-parts/our-inventory/?branch%5B%5D=1457182&nb_items=42&sort=date",
        'Cornwall': "https://kennyupull.com/auto-parts/our-inventory/?branch%5B%5D=1576848&nb_items=42&sort=date"
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        logger.info(f"Attempting to scrape {location} inventory")
        # Add delay to prevent rate limiting
        time.sleep(2)
        
        # First try to get the page
        response = requests.get(urls[location], headers=headers, timeout=30)
        response.raise_for_status()
        
        logger.info(f"Successfully fetched page for {location}")
        
        # For testing/debugging, return some sample data
        sample_inventory = [
            {
                'title': '2015 Honda Civic',
                'image_url': 'https://via.placeholder.com/150',
                'detail_url': '#',
                'branch': location,
                'year': '2015',
                'make': 'Honda',
                'model': 'Civic'
            },
            {
                'title': '2018 Toyota Camry',
                'image_url': 'https://via.placeholder.com/150',
                'detail_url': '#',
                'branch': location,
                'year': '2018',
                'make': 'Toyota',
                'model': 'Camry'
            },
            {
                'title': '2016 Ford Focus',
                'image_url': 'https://via.placeholder.com/150',
                'detail_url': '#',
                'branch': location,
                'year': '2016',
                'make': 'Ford',
                'model': 'Focus'
            }
        ]
        
        return sample_inventory

    except requests.RequestException as e:
        logger.error(f"Request error for {location}: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"General error for {location}: {str(e)}")
        return []

@app.route('/')
def home():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Kenny U-Pull Inventory Viewer</title>
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
                text-decoration: none;
                transition: background-color 0.3s;
            }
            .button:hover { 
                background-color: #0056b3; 
            }
            .status {
                margin-top: 20px;
                padding: 10px;
                border-radius: 5px;
                background-color: #f8f9fa;
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
            <h1 style="color: #007bff;">Kenny U-Pull Inventory Viewer</h1>
            <div class="status">
                ℹ️ Note: This is a demo version showing sample data while we work on live data integration.
            </div>
            <div class="button-container">
                <a href="/scrape/Ottawa" class="button">View Ottawa</a>
                <a href="/scrape/Gatineau" class="button">View Gatineau</a>
                <a href="/scrape/Cornwall" class="button">View Cornwall</a>
            </div>
        </div>
    </body>
    </html>
    """)

@app.route('/scrape/<location>')
def scrape(location):
    logger.info(f"Received request for {location}")
    inventory = scrape_kenny_upull(location)
    
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
            .back-link {
                display: block;
                text-align: center;
                margin: 20px;
                color: #007bff;
                text-decoration: none;
            }
            .status {
                margin: 20px 0;
                padding: 10px;
                border-radius: 5px;
                background-color: #f8f9fa;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="color: #007bff; text-align: center;">{{ location }} Inventory</h1>
            <div class="status">
                ℹ️ Currently showing sample data for demonstration purposes.
            </div>
            <div class="grid">
            {% for car in inventory %}
                <div class="card">
                    <img src="{{ car['image_url'] }}" alt="{{ car['title'] }}" onerror="this.src='https://via.placeholder.com/150'">
                    <h3>{{ car['title'] }}</h3>
                    <p>Branch: {{ car['branch'] }}</p>
                </div>
            {% endfor %}
            </div>
            <a href="/" class="back-link">Back to Home</a>
        </div>
    </body>
    </html>
    """, location=location, inventory=inventory)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
