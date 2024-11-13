# Universal Scraper

This script enables users to scrape data from a webpage and store it in a MongoDB database. The extracted data is structured based on JSON objects specified in the prompt, providing a standardized way to collect detailed product information, metadata, tags, and more. The script can process single URLs or a batch of URLs from a CSV file, and it utilizes both Jina AI and OpenAI APIs for data extraction.

## Setup

1. **Environment Variables**:  
   Make sure you have a `.env` file with the following variables:
   - `JINA_API_KEY`: Your Jina AI API key.
   - `OPENAI_API_KEY`: Your OpenAI API key.
   - `MONGODB_URI`: URI for MongoDB connection.

2. **Dependencies**:  
   Install the required libraries with:
   ```bash
   pip install python-dotenv requests openai pymongo
   ```

## Usage

### JSON Prompt Customization

The script uses JSON structures within the OpenAI prompt to extract specific data fields. **Modify these JSON objects in the `extract_structured_data` method to suit your desired data fields and structure**. This customization allows you to capture precisely the data you need from each webpage.

### Running the Script

1. **Single URL Processing**  
   To scrape data from a single URL:
   ```python
   scraper.process_single_url("https://example.com/product", "output.json")
   ```

2. **Multiple URLs from a CSV File**  
   To process multiple URLs stored in a CSV file (one URL per line):
   ```python
   scraper.process_urls('urls.csv', 'scraped_data.json')
   ```

### Output

- **MongoDB Storage**: Scraped data is stored in MongoDB, with each entry associated with a unique document ID based on its URL.
- **JSON Output File**: If an output file is specified, the results will also be saved as a JSON file.

## Additional Notes

- **CSV Input**: The script reads URLs from a CSV file where each row contains a single URL.
- **Error Handling**: Includes basic error handling for both network and database operations.
- **Debugging**: The script prints debug information for requests, headers, and MongoDB operations to help troubleshoot issues.

