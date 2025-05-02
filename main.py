from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from flask_cors import CORS
import traceback
import logging
import gc
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({
        "message": "Welcome to HTML Cleaner API",
        "usage": "POST /clean with 'html' and optional 'keywords' fields"
    })

@app.route('/clean', methods=['POST'])
def clean_html():
    start_time = time.time()
    try:
        # Log request size
        content_length = request.content_length
        logger.info(f"Received request with content length: {content_length} bytes")
        
        if content_length and content_length > 5 * 1024 * 1024:  # 5MB limit
            return jsonify({"error": "HTML content too large (>5MB)"}), 413
        
        try:
            data = request.get_json(force=True)
        except Exception as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return jsonify({"error": "Invalid JSON format", "details": str(e)}), 400
        
        html = data.get('html')
        keywords = data.get('keywords', [])
        
        # Basic validation
        if not html:
            return jsonify({"error": "Missing 'html' field"}), 400
        if not isinstance(html, str):
            return jsonify({"error": "'html' must be a string"}), 400
        if not isinstance(keywords, list):
            return jsonify({"error": "'keywords' must be a list of strings"}), 400
        
        logger.info(f"Processing HTML content of length {len(html)} with keywords: {keywords}")
        
        # Use lxml parser for better performance with large HTML
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove scripts and styles to reduce memory footprint
        for tag in soup(["script", "style", "iframe", "canvas", "svg"]):
            tag.decompose()
        
        # Try extracting URL from meta or base tags
        url = ""
        base = soup.find('base', href=True)
        if base:
            url = base['href']
        else:
            meta = soup.find('meta', attrs={"property": "og:url"})
            if meta:
                url = meta.get('content', '')
        
        # More efficient approach to find keyword matches
        best_match = {
            "url": url,
            "heading": None,
            "article": None,
            "keywords": [],
            "match_count": 0
        }
        
        # Process in smaller chunks instead of all articles at once
        for tag_name in ['article', 'section', 'div']:
            blocks = soup.find_all(tag_name, limit=50)  # Limit to prevent processing too many
            
            for block in blocks:
                if block.get_text(strip=True):  # Skip empty blocks
                    text = block.get_text(separator=' ', strip=True).lower()
                    count = sum(text.count(k.lower()) for k in keywords if k)
                    
                    if count > best_match["match_count"]:
                        heading = block.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                        snippet = ' '.join(text.split()[:100])  # first 100 words
                        
                        best_match.update({
                            "match_count": count,
                            "heading": heading.get_text(strip=True) if heading else None,
                            "article": snippet,
                            "keywords": [k for k in keywords if k and k.lower() in text]
                        })
        
        # Extract text more efficiently
        paragraphs = soup.find_all(['p', 'div'], limit=100)  # Limit paragraphs to process
        full_text = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        full_text = ' '.join(full_text.split()[:500])  # Limit to first 500 words
        
        # Force garbage collection to free memory
        soup.decompose()
        soup = None
        gc.collect()
        
        processing_time = time.time() - start_time
        logger.info(f"Processing completed in {processing_time:.2f} seconds")
        
        return jsonify({
            "url": best_match['url'],
            "heading": best_match['heading'],
            "article_context": best_match['article'],
            "matched_keywords": best_match['keywords'],
            "cleanText": full_text,
            "processing_time_seconds": processing_time
        })
        
    except MemoryError:
        logger.error("Memory error occurred while processing HTML")
        gc.collect()  # Try to recover memory
        return jsonify({
            "error": "Out of memory",
            "details": "The HTML content is too large to process with available resources"
        }), 500
        
    except Exception as e:
        logger.error(f"Error processing HTML: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Processing Error",
            "details": str(e),
            "type": type(e).__name__
        }), 500

if __name__ == '__main__':
    # Get port from environment variable or use 5000 as default
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
