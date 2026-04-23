import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

load_dotenv()

app = Flask(__name__)
CORS(app)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def scrape_etsy(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    print("PAGE TITLE:", soup.title.string if soup.title else "NONE")
    print("H1 TAGS:", [h.get_text(strip=True)[:50] for h in soup.find_all("h1")])

    # Hämta titel
    title = ""
    title_tag = soup.find("h1")
    if title_tag:
        title = title_tag.get_text(strip=True)

    # Hämta beskrivning
    desc = ""
    desc_tag = soup.find("p", {"data-product-details-description-text-content": True})
    if not desc_tag:
        desc_tag = soup.find("div", class_=lambda c: c and "description" in c.lower())
    if desc_tag:
        desc = desc_tag.get_text(strip=True)

    return title, desc


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
    result = json.loads(raw.strip())

    return jsonify(result)

@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.json
    url = data.get("url", "")
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    try:
        title, desc = scrape_etsy(url)
        return jsonify({"title": title, "description": desc})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)