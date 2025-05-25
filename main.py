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

@app.route('/clean', methods=['POST'])
def clean_html():
    start_time = time.time()
    try:
        content_type = request.headers.get('Content-Type', '')
        if 'application/json' in content_type.lower():
            data = request.get_json(force=True)
        else:
            return jsonify({"error": "Unsupported Content-Type"}), 400

        html_content = data.get('html', '')
        keywords = data.get('keywords', [])

        if not html_content or not isinstance(html_content, str):
            return jsonify({"error": "Missing or invalid 'html' field"}), 400
        if not isinstance(keywords, list):
            return jsonify({"error": "'keywords' must be a list of strings"}), 400

        soup = BeautifulSoup(html_content, 'lxml')

        matches = []
        total_keyword_count = 0

        for art in soup.find_all('article'):
            text = art.get_text(separator=' ', strip=True)
            clean_text = html.unescape(text)
            clean_text = re.sub(r'\s+', ' ', clean_text)

            lower_text = clean_text.lower()
            keyword_data = []
            local_keyword_count = 0

            for kw in keywords:
                if kw:
                    count = lower_text.count(kw.lower())
                    if count > 0:
                        keyword_data.append({"keyword": kw, "count": count})
                        local_keyword_count += count

            if keyword_data:
                heading_tag = art.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                heading = heading_tag.get_text(strip=True) if heading_tag else None

                # Look for article URL
                link_tag = art.find('a', href=True)
                if not link_tag and art.parent and art.parent.name == "a" and art.parent.has_attr("href"):
                    link_tag = art.parent
                article_url = link_tag['href'] if link_tag and link_tag.has_attr('href') else None

                snippet = ' '.join(clean_text.split()[:100])
                matches.append({
                    "heading": heading,
                    "article_context": snippet,
                    "article_url": article_url,
                    "matched_keywords": keyword_data
                })
              

                total_keyword_count += local_keyword_count

        processing_time = round(time.time() - start_time, 2)

        return jsonify({
            "total_matched_articles": len(matches),
            "total_keywords_matched": total_keyword_count,
            "matches": matches,
            "processing_time_seconds": processing_time
        })

    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
