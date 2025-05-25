from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from flask_cors import CORS
import logging
import time
import html  # for decoding HTML entities
import re     # for normalizing text
from urllib.parse import urljoin

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
        content_length = request.content_length
        logger.info(f"Received request with content length: {content_length} bytes")

        if content_length and content_length > 5 * 1024 * 1024:
            return jsonify({"error": "HTML content too large (>5MB)"}), 413

        content_type = request.headers.get('Content-Type', '')
        logger.info(f"Content-Type: {content_type}")

        try:
            if 'application/json' in content_type.lower():
                data = request.get_json(force=True)
            else:
                raw_data = request.data.decode('utf-8', errors='replace')
                data = {
                    'html': raw_data,
                    'keywords': [k.strip() for k in request.args.get('keywords', '').split(',') if k.strip()]
                }
        except Exception as e:
            logger.error(f"Data parsing error: {str(e)}")
            return jsonify({"error": "Invalid data format", "details": str(e)}), 400

        html_content = data.get('html', '')
        keywords = data.get('keywords', [])

        if not html_content:
            return jsonify({"error": "Missing 'html' field"}), 400
        if not isinstance(html_content, str):
            return jsonify({"error": "'html' must be a string"}), 400
        if not isinstance(keywords, list):
            return jsonify({"error": "'keywords' must be a list of strings"}), 400

        logger.info(f"Processing HTML content of length {len(html_content)} with keywords: {keywords}")

        soup = BeautifulSoup(html_content, 'lxml')
        for tag in soup(["script", "style", "iframe", "canvas", "svg"]):
            tag.decompose()

        # Initialize results
        matches = []
        total_matched_articles = 0
        total_keywords_matched = 0

        # Extracting article content and counting keywords
        for tag_name in ['article', 'section', 'div']:
            blocks = soup.find_all(tag_name, limit=50)

            for block in blocks:
                if block.get_text(strip=True):
                    raw_text = block.get_text(separator=' ', strip=True)
                    clean_text = html.unescape(raw_text)
                    clean_text = re.sub(r'[\r\n\t]+', ' ', clean_text)
                    clean_text = re.sub(r'[^\w\s]', '', clean_text)
                    lower_text = clean_text.lower()

                    matched_keywords = [
                        k for k in keywords if k and k.lower() in lower_text
                    ]
                    keyword_count = len(matched_keywords)

                    if keyword_count > 0:
                        heading = block.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                        article_url = ""
                        links = block.find_all('a', href=True)

                        for link in links:
                            if 'read more' in link.text.lower() or 'news' in link['href']:
                                article_url = link['href']
                                break
                        article_url = urljoin(request.host_url, article_url) if article_url else ""

                        matches.append({
                            "heading": heading.get_text(strip=True) if heading else "No Heading",
                            "article_context": ' '.join(clean_text.split()[:100]),
                            "article_url": article_url,
                            "matched_keywords": [{"keyword": k, "count": lower_text.count(k.lower())} for k in matched_keywords]
                        })
                        
                        total_matched_articles += 1
                        total_keywords_matched += keyword_count

        processing_time = time.time() - start_time
        logger.info(f"Processing completed in {processing_time:.2f} seconds")

        # Return the response with all matched articles
        return jsonify({
            "matches": matches,
            "total_matched_articles": total_matched_articles,
            "total_keywords_matched": total_keywords_matched,
            "processing_time_seconds": processing_time
        })

    except Exception as e:
        logger.error(f"Error processing HTML: {str(e)}")
        return jsonify({
            "error": "Processing Error",
            "details": str(e),
            "type": type(e).__name__
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
