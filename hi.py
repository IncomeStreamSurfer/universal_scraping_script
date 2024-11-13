import os
import json
import csv
from typing import List, Dict
from dotenv import load_dotenv
import requests
from openai import OpenAI
from datetime import datetime
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
import hashlib

# Load environment variables
load_dotenv()

# Get API keys and check if they exist
JINA_API_KEY = os.getenv('JINA_API_KEY')
if not JINA_API_KEY:
    raise ValueError("JINA_API_KEY not found in environment variables")

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
MONGODB_URI = os.getenv('MONGODB_URI')

class UniversalScraper:
    def __init__(self, db_name: str = "web_scraper", collection_name: str = None):
        # Print debug info for headers
        self.jina_headers = {
            'Authorization': f'Bearer {JINA_API_KEY}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-With-Links-Summary': 'true',
            'X-With-Images-Summary': 'true'
        }
        print("Debug - Authorization header:", self.jina_headers['Authorization'][:15] + "...")

        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        
        # MongoDB setup
        self.mongo_client = MongoClient(MONGODB_URI)
        self.db: Database = self.mongo_client[db_name]
        
        if collection_name is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            collection_name = f"product_data_{timestamp}"
        
        self.collection: Collection = self.db[collection_name]
        print(f"Using MongoDB collection: {collection_name}")

    def generate_document_id(self, url: str) -> str:
        """Generate a unique ID for a document based on its URL."""
        return hashlib.md5(url.encode()).hexdigest()

    def save_to_mongodb(self, data: Dict, url: str) -> bool:
        """Save scraped data to MongoDB with error handling."""
        try:
            # Generate a unique ID based on the URL
            doc_id = self.generate_document_id(url)
            
            # Add metadata if not present
            if 'metadata' not in data:
                data['metadata'] = {}
            
            data['metadata'].update({
                'source_url': url,
                'scrape_timestamp': datetime.now().isoformat(),
                '_id': doc_id
            })
            
            # Update if exists, insert if not
            self.collection.update_one(
                {'_id': doc_id},
                {'$set': data},
                upsert=True
            )
            
            print(f"Successfully saved data for {url} to MongoDB")
            return True
        except Exception as e:
            print(f"Error saving to MongoDB: {str(e)}")
            return False

    def fetch_page_content(self, url: str) -> Dict:
        """Fetch page content with improved error handling and debugging."""
        try:
            print(f"\nDebug - Fetching URL: {url}")
            print("Debug - Using headers:", json.dumps(self.jina_headers, indent=2))
            
            response = requests.post(
                'https://r.jina.ai/',
                headers=self.jina_headers,
                json={'url': url},
                timeout=30
            )
            
            print(f"Debug - Response status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Debug - Error response content: {response.text}")
                response.raise_for_status()
                
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {str(e)}")
            if hasattr(e, 'response') and e.response:
                print(f"Debug - Full error response: {e.response.text}")
            return None

    def extract_structured_data(self, content: str, url: str) -> Dict:
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert e-commerce data extractor and product classifier. Extract all available information from the provided content and format it according to the JSON structure provided. Generate comprehensive tags covering: product type, style, color, material, occasion, season, fit, trend, demographic, price tier. If information is not available, use null for single values or empty arrays [] for lists. Always generate at least 20 descriptive tags."
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze this webpage content and extract all available information into the following structure. The webpage content is: {content}

Please format the response exactly like this JSON structure, filling in all available information:

{{
    "product_details": {{
        "title": "Complete product title",
        "brand": "Brand name",
        "sku": "Product SKU/ID",
        "main_image": "Primary product image URL",
        "secondary_images": ["URL1", "URL2"],
        "price_information": {{
            "current_price": "Current price with currency",
            "original_price": "Original price if available",
            "currency": "Currency code (e.g., USD)",
            "discount_percentage": "Calculated discount if any",
            "price_per_unit": "Price per unit if available",
            "bulk_pricing": [
                {{
                    "quantity": "Minimum quantity",
                    "price": "Price at this quantity"
                }}
            ]
        }},
        "availability": {{
            "status": "in_stock/out_of_stock/preorder",
            "quantity_available": "Stock level if shown",
            "delivery_estimate": "Delivery timeframe"
        }}
    }},
    "product_content": {{
        "short_description": "Brief product overview",
        "full_description": "Complete product description",
        "key_features": ["Feature 1", "Feature 2"],
        "bullet_points": ["Point 1", "Point 2"],
        "usage_instructions": ["Step 1", "Step 2"],
        "highlights": [
            {{
                "title": "Highlight title",
                "description": "Highlight description"
            }}
        ]
    }},
    "technical_details": {{
        "dimensions": {{
            "length": "Length with unit",
            "width": "Width with unit",
            "height": "Height with unit",
            "weight": "Weight with unit",
            "package_dimensions": {{
                "length": "Package length",
                "width": "Package width",
                "height": "Package height",
                "weight": "Package weight"
            }}
        }},
        "specifications": [
            {{
                "category": "Spec category",
                "attributes": [
                    {{
                        "name": "Spec name",
                        "value": "Spec value",
                        "unit": "Unit if applicable"
                    }}
                ]
            }}
        ],
        "materials": ["Material 1", "Material 2"],
        "certifications": ["Cert 1", "Cert 2"],
        "compatibility": ["Compatible item 1", "Compatible item 2"]
    }},
    "classification_tags": {{
        "product_type_tags": ["polo shirt", "casual wear", "sportswear"],
        "style_tags": ["classic", "modern", "preppy", "formal", "casual"],
        "color_tags": ["navy blue", "dark blue", "solid color"],
        "material_tags": ["cotton", "pique cotton", "natural fiber"],
        "occasion_tags": ["casual", "semi-formal", "business casual", "weekend"],
        "season_tags": ["summer", "spring", "year-round"],
        "fit_tags": ["regular fit", "classic fit", "comfortable"],
        "trend_tags": ["timeless", "classic style", "sustainable"],
        "demographic_tags": ["men", "adult", "professional"],
        "price_tier_tags": ["luxury", "high-end", "premium"],
        "all_tags": [
            # At least 20 comprehensive tags combining all aspects
            "polo shirt",
            "navy blue",
            "cotton",
            "luxury brand",
            "business casual",
            "men's fashion",
            "summer wear",
            "classic style",
            "comfortable fit",
            "professional attire",
            "premium quality",
            "solid color",
            "casual elegance",
            "weekend wear",
            "natural materials",
            "breathable fabric",
            "versatile clothing",
            "smart casual",
            "timeless design",
            "high-end fashion"
        ]
    }},
    "additional_information": {{
        "categories": ["Category 1", "Category 2"],
        "model_number": "Model number if available",
        "manufacturer": {{
            "name": "Manufacturer name",
            "country_of_origin": "Manufacturing country",
            "contact_info": "Manufacturer contact details"
        }},
        "warranty": {{
            "duration": "Warranty period",
            "type": "Warranty type",
            "coverage": ["Coverage detail 1", "Coverage detail 2"]
        }},
        "package_contents": ["Item 1", "Item 2"],
        "related_products": [
            {{
                "title": "Related product name",
                "url": "Related product URL",
                "relationship_type": "Similar/Accessory/Complement"
            }}
        ]
    }},
    "purchase_information": {{
        "shipping": {{
            "methods": [
                {{
                    "name": "Shipping method",
                    "cost": "Shipping cost",
                    "estimated_days": "Delivery estimate"
                }}
            ],
            "free_shipping_threshold": "Min order for free shipping",
            "restrictions": ["Restriction 1", "Restriction 2"]
        }},
        "return_policy": {{
            "duration": "Return window",
            "conditions": ["Condition 1", "Condition 2"],
            "restocking_fee": "Fee if applicable"
        }},
        "payment_methods": ["Method 1", "Method 2"]
    }},
    "reviews_and_ratings": {{
        "average_rating": "Overall rating",
        "total_reviews": "Number of reviews",
        "rating_distribution": {{
            "5_star": "Count of 5 star reviews",
            "4_star": "Count of 4 star reviews",
            "3_star": "Count of 3 star reviews",
            "2_star": "Count of 2 star reviews",
            "1_star": "Count of 1 star reviews"
        }},
        "featured_reviews": [
            {{
                "rating": "Review rating",
                "title": "Review title",
                "content": "Review content",
                "author": "Reviewer name",
                "date": "Review date",
                "verified_purchase": "true/false"
            }}
        ]
    }},
    "metadata": {{
        "source_url": "{url}",
        "scrape_timestamp": "{datetime.now().isoformat()}",
        "last_updated": "Product last updated date if shown",
        "schema_version": "1.0"
    }}
}}"""
                    }
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error extracting structured data: {str(e)}")
            return None

    def process_single_url(self, url: str, output_file: str = None):
        """Process a single URL."""
        print(f"\nProcessing URL: {url}")
        page_content = self.fetch_page_content(url)
        
        if page_content and 'data' in page_content:
            content = page_content['data'].get('content', '')
            structured_data = self.extract_structured_data(content, url)
            
            if structured_data:
                # Save to MongoDB
                self.save_to_mongodb(structured_data, url)
                
                # Save to file if specified
                if output_file:
                    self.save_results([structured_data], output_file)
                    print(f"Results saved to {output_file}")
        else:
            print("Failed to fetch page content")

    def read_urls_from_csv(self, filename: str) -> List[str]:
        """Read URLs from a CSV file."""
        urls = []
        with open(filename, 'r') as file:
            reader = csv.reader(file)
            for row in reader:
                if row:  # Skip empty rows
                    urls.append(row[0].strip())
        return urls

    def save_results(self, results: Dict, output_file: str):
        """Save results to a JSON file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    def process_urls(self, input_csv: str, output_file: str = None):
        """Process multiple URLs from a CSV file."""
        urls = self.read_urls_from_csv(input_csv)
        all_results = []

        for url in urls:
            print(f"\nProcessing {url}")
            page_content = self.fetch_page_content(url)
            
            if page_content and 'data' in page_content:
                content = page_content['data'].get('content', '')
                structured_data = self.extract_structured_data(content, url)
                
                if structured_data:
                    # Save to MongoDB
                    self.save_to_mongodb(structured_data, url)
                    all_results.append(structured_data)
        
        # Optionally save to file if output_file is provided
        if output_file:
            self.save_results(all_results, output_file)
            print(f"Results saved to {output_file}")

def main():
    # Create a new scraper instance with a unique collection name
    collection_name = f"product_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    scraper = UniversalScraper(db_name="web_scraper", collection_name=collection_name)
    
    # You can either process a single URL
    # scraper.process_single_url("https://example.com/product", "single_product.json")
    
    # Or process multiple URLs from a CSV file
    scraper.process_urls('urls.csv', 'scraped_data.json')

if __name__ == "__main__":
    main()