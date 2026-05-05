import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import anthropic
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import stripe


load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")



app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def get_listing_id(url):
    # Plockar ut listing ID från Etsy URL
    # t.ex. https://www.etsy.com/listing/4420009795/...
    parts = url.split("/listing/")
    if len(parts) > 1:
        return parts[1].split("/")[0]
    return None

def fetch_etsy_listing(listing_id):
    api_key = os.getenv("ETSY_API_KEY")
    print("API KEY:", api_key[:20] if api_key else "NONE")
    url = f"https://openapi.etsy.com/v3/application/listings/{listing_id}"
    headers = {"x-api-key": api_key}
    response = requests.get(url, headers=headers)
    print("ETSY STATUS:", response.status_code)
    print("ETSY RESPONSE:", response.text[:500])
    data = response.json()
    return data

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.json
    url = data.get("url", "")
    print("GOT URL:", url[:80])
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    try:
        listing_id = get_listing_id(url)
        print("LISTING ID:", listing_id)
        if not listing_id:
            return jsonify({"error": "Could not find listing ID in URL"}), 400

        listing = fetch_etsy_listing(listing_id)
        print("LISTING KEYS:", listing.keys())

        title = listing.get("title", "")
        desc = listing.get("description", "")
        tags = ", ".join(listing.get("tags", []))

        return jsonify({"title": title, "description": desc, "tags": tags})
    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500



@app.route("/analyze", methods=["POST"])

def analyze():
    data = request.json
    title = data.get("title", "")
    tags = data.get("tags", "")
    desc = data.get("description", "")

    prompt = f"""You are an expert Etsy SEO consultant who has helped thousands of sellers grow their shops. You have deep knowledge of the Etsy search algorithm, buyer psychology, and what makes listings convert.

Analyze this Etsy listing critically and honestly. Be specific - avoid vague advice like "improve your title". Instead say exactly what words to add or remove and why.

Return ONLY a valid JSON object with this exact structure, no markdown, no extra text:

{{
  "overall_score": 6,
  "overall_summary": "Your listing is missing key search terms and your title buries the most important keywords at the end where Etsy's algorithm weighs them less.",
  "title": {{
    "score": 5,
    "issues": [
      "First 3 words are not your strongest keywords - Etsy weights these heavily",
      "Missing occasion keywords like 'gift for her' or 'birthday gift' which drive high purchase intent"
    ],
    "improved_version": "Sterling Silver Stacking Ring - Minimalist Gift for Her - Handmade Jewelry"
  }},
  "tags": {{
    "score": 4,
    "missing_tags": ["sterling silver ring", "minimalist jewelry", "gift for women", "stacking ring set", "dainty ring"],
    "explanation": "You are only using 8 of 13 available tag slots. Each unused tag slot is a missed opportunity to appear in search results."
  }},
  "description": {{
    "score": 7,
    "issues": [
      "Opening sentence does not hook the buyer - lead with the transformation or feeling, not the product",
      "No mention of processing or shipping time which reduces buyer confidence"
    ],
    "improved_opening": "Looking for a gift she will wear every single day? This handcrafted sterling silver ring..."
  }},
  "photos": {{
    "feedback": "Make sure your first photo has a clean white or neutral background. Lifestyle photos showing the item being worn convert significantly better than flat lay photos alone."
  }},
  "quick_wins": [
    "Move your strongest keyword to the very first word of your title - this alone can improve ranking",
    "Fill all 13 tag slots - you are leaving free visibility on the table",
    "Add a lifestyle photo showing the product in use",
    "Mention exact dimensions and materials in the first 3 lines of your description"
  ]
}}

Be brutally honest. Sellers need real feedback, not flattery.

Listing to analyze:
TITLE: {title}
TAGS: {tags}
DESCRIPTION: {desc}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    raw = message.content[0].text
    print("RAW RESPONSE:", raw)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    # Hitta första { och sista } för att extrahera ren JSON
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]
    result = json.loads(raw)

    return jsonify(result)


@app.route("/create-checkout", methods=["POST"])
def create_checkout():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "ListingIQ Pro",
                        "description": "Unlimited Etsy listing analyses"
                    },
                    "unit_amount": 399,
                    "recurring": {"interval": "month"}
                },
                "quantity": 1
            }],
            mode="subscription",
            success_url="https://listing-iq-production.up.railway.app/success.html",
            cancel_url="https://listing-iq-production.up.railway.app/index.html"
        )
        return jsonify({"url": session.url})
    except Exception as e:
        print("STRIPE ERROR:", str(e))
        return jsonify({"error": str(e)}), 500





if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)