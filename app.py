import os
import requests
from flask import Flask, render_template_string
import logging
from bs4 import BeautifulSoup
import time
import json

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_sample_inventory(location):
    return [
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
        }
    ]

def scrape_kenny_upull(location):
    urls = {
        'Ottawa': "https://kennyupull.com/auto-parts/our-inventory/?branch%5B%5D=1457192&nb_items=42&sort=date",
        'Gatineau': "https://kennyupull.com/auto-parts/our-inventory/?branch%5B%5D=1457182&nb_items=42&sort=date",
        'Cornwall': "https://kennyupull.com/auto-parts/our-inventory/?branch%5B%5D=1576848&nb_items=42&sort=date"
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        logger.info(f"Starting scrape for {location}")
        
        # Add delay to prevent rate limiting
        time.sleep(1)
        
        response = requests.get(urls[location], headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        inventory = []
        
        # Find all vehicle items
        vehicle_containers = soup.find_all('div', class_='vehicle-container')
        
        if not vehicle_containers:
            logger.warning(f"No vehicles found for {location}, falling back to sample data")
            return get_sample_inventory(location)
        
        for container in vehicle_containers:
            try:
                # Get image
                image_tag = container.find('img')
                image_url = image_tag.get('data-src') if image_tag else 'https://via.placeholder.com/150'
                title = image_tag.get('alt', 'Unknown Vehicle') if image_tag else 'Unknown Vehicle'
                
                # Get link
                link_tag = container.find('a')
                detail_url = link_tag.get('href', '#') if link_tag else '#'
                
                # Extract year, make, model from title
                parts = title.split()
                year = parts[0] if parts else "Unknown"
                make = parts[1] if len(parts) > 1 else "Unknown"
                model = parts[2] if len(parts) > 2 else "Unknown"
                
                car = {
                    'title': title,
                    'image_url': image_url,
                    'detail_url': detail_url,
                    'branch': location,
                    'year': year,
                    'make': make,
                    'model': model
                }
                
                inventory.append(car)
                logger.info(f"Successfully processed vehicle: {title}")
                
            except Exception as e:
                logger.error(f"Error processing vehicle: {str(e)}")
                continue
        
        if not inventory:
            logger.warning(f"No vehicles could be processed for {location}, falling back to sample data")
            return get_sample_inventory(location)
            
        return inventory
        
    except requests.RequestException as e:
        logger.error(f"Request error for {location}: {str(e)}")
        return get_sample_inventory(location)
    except Exception as e:
        logger.error(f"General error for {location}: {str(e)}")
        return get_sample_inventory(location)

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
            .loading {
                display: none;
                margin-top: 20px;
            }
            @media (max-width: 600px) { 
                .button { 
                    width: 100%; 
                } 
            }
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
            .card h3 {
                margin: 10px 0;
                color: #333;
            }
            .card p {
                margin: 5px 0;
                color: #666;
            }
            .back-link {
                display: inline-block;
                padding: 10px 20px;
                background-color: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px;
                transition: background-color 0.3s;
            }
            .back-link:hover {
                background-color: #0056b3;
            }
            .notice {
                background-color: #fff3cd;
                border: 1px solid #ffeeba;
                color: #856404;
                padding: 10px;
                margin: 20px 0;
                border-radius: 5px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="color: #007bff; text-align: center;">{{ location }} Inventory</h1>
            {% if inventory|length == 2 %}
            <div class="notice">
                ⚠️ Showing sample data due to temporary access issues. Please try again later for live data.
            </div>
            {% endif %}
            <div class="grid">
            {% for car in inventory %}
                <div class="card">
                    <img src="{{ car['image_url'] }}" alt="{{ car['title'] }}" onerror="this.src='https://via.placeholder.com/150'">
                    <h3>{{ car['title'] }}</h3>
                    <p>Branch: {{ car['branch'] }}</p>
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
