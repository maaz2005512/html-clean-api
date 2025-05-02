from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from flask_cors import CORS
import traceback
import logging
import gc
import time
import html  # for decoding HTML entities
import re     # for normalizing text

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

@app.route('/debug', methods=['POST'])
def debug_request():
    try:
        result = {
            "content_type": request.headers.get('Content-Type', 'None'),
            "content_length": request.content_length,
            "headers": dict(request.headers),
            "form_data": dict(request.form),
            "args": dict(request.args)
        }
        try:
            raw_data = request.data.decode('utf-8', errors='replace')
            result["raw_data_preview"] = raw_data[:500] + ("..." if len(raw_data) > 500 else "")
        except Exception as e:
            result["raw_data_error"] = str(e)

        try:
            json_data = request.get_json(force=True, silent=True)
            if json_data:
                result["json_parsable"] = True
                result["json_keys"] = list(json_data.keys()) if isinstance(json_data, dict) else "Not a dictionary"
            else:
                result["json_parsable"] = False
        except Exception as e:
            result["json_error"] = str(e)
            result["json_parsable"] = False

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()})

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
            elif 'application/x-www-form-urlencoded' in content_type.lower():
                data = {
                    'html': request.form.get('html', ''),
                    'keywords': [k.strip() for k in request.form.get('keywords', '').split(',') if k.strip()]
                }
            elif 'multipart/form-data' in content_type.lower():
                data = {
                    'html': request.form.get('html', ''),
                    'keywords': [k.strip() for k in request.form.get('keywords', '').split(',') if k.strip()]
                }
            else:
                raw_data = request.data.decode('utf-8', errors='replace')
                try:
                    import json
                    data = json.loads(raw_data)
                except json.JSONDecodeError:
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

        url = ""
        base = soup.find('base', href=True)
        if base:
            url = base['href']
        else:
            meta = soup.find('meta', attrs={"property": "og:url"})
            if meta:
                url = meta.get('content', '')

        best_match = {
            "url": url,
            "heading": None,
            "article": None,
            "keywords": [],
            "match_count": 0
        }

        for tag_name in ['article', 'section', 'div']:
            blocks = soup.find_all(tag_name, limit=50)

            for block in blocks:
                if block.get_text(strip=True):
                    raw_text = block.get_text(separator=' ', strip=True)
                    clean_text = html.unescape(raw_text)
                    clean_text = re.sub(r'[\r\n\t]+', ' ', clean_text)
                    clean_text = re.sub(r'[^\w\s]', '', clean_text)
                    lower_text = clean_text.lower()

                    count = sum(lower_text.count(k.lower()) for k in keywords if k)
                    if count > best_match["match_count"]:
                        heading = block.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                        snippet = ' '.join(clean_text.split()[:100])
                        best_match.update({
                            "match_count": count,
                            "heading": heading.get_text(strip=True) if heading else None,
                            "article": snippet,
                            "keywords": [k for k in keywords if k and k.lower() in lower_text]
                        })

        paragraphs = soup.find_all(['p', 'div'], limit=100)
        full_text = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        full_text = ' '.join(full_text.split()[:500])

        soup.decompose()
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
        gc.collect()
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
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
