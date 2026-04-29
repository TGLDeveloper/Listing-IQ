// ── State ────────────────────────────────────────────────────
let usesLeft = parseInt(localStorage.getItem('usesLeft') ?? '3');

//fetcha url funktion
async function fetchFromUrl() {
  const url = document.getElementById('listing-url').value.trim();
  if (!url) { alert('Please enter an Etsy URL first.'); return; }

  const btn = document.getElementById('fetch-btn');
  btn.textContent = 'Fetching...';
  btn.disabled = true;

  try {
    const response = await fetch("https://listing-iq-production.up.railway.app/scrape", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });
    const data = await response.json();

    if (data.error) { alert('Could not fetch listing. Try entering manually.'); return; }
    if (data.title) document.getElementById('listing-title').value = data.title;
    if (data.description) document.getElementById('listing-desc').value = data.description;

  } catch (err) {
    alert('Could not fetch listing. Try entering manually.');
  } finally {
    btn.textContent = 'Fetch';
    btn.disabled = false;
  }
}



// ── Analyze function ─────────────────────────────────────────
async function analyzeListing() {
  const title = document.getElementById('listing-title').value.trim();
  const tags  = document.getElementById('listing-tags').value.trim();
  const desc  = document.getElementById('listing-desc').value.trim();

  // Basic validation
  if (!title && !desc) {
    alert('Please fill in at least your title and description.');
    return;
  }

  if (usesLeft <= 0) {
    const response = await fetch("https://listing-iq-production.up.railway.app/create-checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
    });
    const data = await response.json();
    if (data.url) window.location.href = data.url;
    return;
  }

  // Hide results, show loading
  document.getElementById('results').style.display = 'none';
  document.getElementById('loading').style.display = 'block';
  document.getElementById('analyze-btn').disabled = true;

  try {
    const response = await fetch("https://listing-iq-production.up.railway.app/analyze", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ title, tags, description: desc })
});
const result = await response.json();

    usesLeft--;
    localStorage.setItem('usesLeft', usesLeft);
    document.querySelector('.uses-left').textContent = `${usesLeft} free analys${usesLeft === 1 ? 'is' : 'es'} left`;

    renderResults(result);

  } catch (err) {
    console.error(err);
    alert('Something went wrong. Please try again.');
  } finally {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('analyze-btn').disabled = false;
  }
}

// ── Render results ────────────────────────────────────────────
function renderResults(data) {
  // Overall score
  document.getElementById('overall-score').textContent = data.overall_score;

  // Title card
  document.getElementById('title-score').textContent = `${data.title.score}/10`;
  renderList('title-issues', data.title.issues);
  document.getElementById('title-improved').textContent = `"${data.title.improved_version}"`;

  // Tags card
  document.getElementById('tags-score').textContent = `${data.tags.score}/10`;
  renderList('tags-missing', data.tags.missing_tags.map(t => `Add tag: "${t}"`));
  document.getElementById('tags-explanation').textContent = data.tags.explanation;

  // Description card
  document.getElementById('desc-score').textContent = `${data.description.score}/10`;
  renderList('desc-issues', data.description.issues);
  document.getElementById('desc-improved').textContent = `"${data.description.improved_opening}"`;

  // Quick wins
  const winsList = document.getElementById('quick-wins');
  winsList.innerHTML = '';
  data.quick_wins.forEach(win => {
    const li = document.createElement('li');
    li.textContent = win;
    winsList.appendChild(li);
  });

  // Show results
  document.getElementById('results').style.display = 'block';
  document.getElementById('results').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderList(elementId, items) {
  const el = document.getElementById(elementId);
  el.innerHTML = '';
  items.forEach(item => {
    const li = document.createElement('li');
    li.textContent = item;
    el.appendChild(li);
  });
}

// ── Mock data (replace with real API call later) ──────────────
async function mockAnalysis(title, tags, desc) {
  // Simulate network delay
  await new Promise(r => setTimeout(r, 1800));

  return {
    overall_score: 5,
    title: {
      score: 4,
      issues: [
        "Title is too short and missing key search terms",
        "Doesn't mention material, occasion, or recipient"
      ],
      improved_version: `${title || 'Handmade Silver Ring'} - Minimalist Stacking Ring - Gift for Her - Sterling Silver Jewelry`
    },
    tags: {
      score: 5,
      missing_tags: ["minimalist jewelry", "gift for women", "stacking ring", "sterling silver"],
      explanation: "You are missing several high-volume search terms that buyers actively use on Etsy. Adding these could significantly increase your visibility."
    },
    description: {
      score: 6,
      issues: [
        "Opening sentence doesn't hook the buyer",
        "No mention of dimensions or sizing info",
        "Missing care instructions"
      ],
      improved_opening: `${desc ? desc.slice(0, 60) + '...' : 'This handcrafted piece is made with care and attention to detail...'}`
    },
    quick_wins: [
      "Add at least 5 more tags — you're leaving free visibility on the table",
      "Put your most important keyword in the first 3 words of your title",
      "Add photos showing the product being worn or used",
      "Include exact dimensions in your description"
    ]
  };
}

async function goToPro() {
  const response = await fetch("https://listing-iq-production.up.railway.app/create-checkout", {
    method: "POST",
    headers: { "Content-Type": "application/json" }
  });
  const data = await response.json();
  if (data.url) window.location.href = data.url;
}



// ── Uppdatera räknaren vid sidladdning ──
const isPro = localStorage.getItem('isPro') === 'true';
document.querySelector('.uses-left').textContent = isPro ? 'Unlimited analyses' : `${usesLeft} free analys${usesLeft === 1 ? 'is' : 'es'} left`;


