"""
FinanceChat â Stateless Flask backend for Vercel + local dev.
All state lives client-side. Every request carries its own context.
PDFs are parsed client-side (PDF.js) â only text is sent here.
"""
import os
import re
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import anthropic

# Project root is one directory up from api/
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
CORS(app)


def parse_with_claude(raw_text: str, api_key: str, filename: str) -> dict:
    """Claude Haiku parses raw statement text into structured JSON."""
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""You are a financial data parser specialising in Indian bank statements (HDFC, IndusInd, SBI, ICICI, Axis, Federal, etc.).

Parse this bank statement and return ONLY valid JSON â no markdown, no explanation.

Return this exact structure:
{{
  "bank": "bank name",
  "account_type": "Savings / Current / etc",
  "account_number": "last 4 digits",
  "period": "DD/MM/YYYY to DD/MM/YYYY",
  "opening_balance": 12345.67,
  "closing_balance": 12345.67,
  "total_credits": 12345.67,
  "total_debits": 12345.67,
  "transactions": [
    {{
      "date": "DD-Mon-YYYY",
      "description": "narration",
      "debit": 0.0,
      "credit": 0.0,
      "balance": 0.0,
      "category": "one of: Academy Revenue, Salary Paid, Rent, EMI/Loan, ATM Withdrawal, Self Transfer, P2P Crypto, FD, Food & Dining, Transfer In, Transfer Out, Other"
    }}
  ]
}}

Filename hint: {filename}

Statement:
{raw_text[:14000]}
"""
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text if msg.content else ""
    text = raw.strip()

    # Strip markdown code fences
    text = re.sub(r'^```(?:json)?\s*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text).strip()

    if not text:
        preview = raw[:200] if raw else "(empty)"
        raise ValueError(f"Claude returned no parseable JSON. Response was: {preview}")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to pull out any {...} block
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            return json.loads(m.group())
        preview = text[:300]
        raise ValueError(f"Claude returned non-JSON: {preview}")


def build_system_prompt(accounts: list) -> str:
    """Build Claude's system prompt from client-provided account data."""
    if not accounts:
        return "No bank statements have been uploaded."

    lines = ["You are FinanceGPT â a sharp, warm financial analyst who specialises in Indian personal and business finances.\n"]
    lines.append("## Bank Statement Data\n")

    for acc in accounts:
        lines.append(f"### {acc.get('bank','Unknown')} â {acc.get('account_type','')} (Â·Â·Â·{str(acc.get('account_number',''))[-4:]})")
        lines.append(f"Period: {acc.get('period','')}")
        lines.append(f"Opening: â¹{acc.get('opening_balance',0):,.2f} | Closing: â¹{acc.get('closing_balance',0):,.2f}")
        lines.append(f"Credits: â¹{acc.get('total_credits',0):,.2f} | Debits: â¹{acc.get('total_debits',0):,.2f}")
        txns = acc.get('transactions', [])
        lines.append(f"Transactions ({len(txns)}):")
        for t in txns[:100]:
            direction = f"+â¹{t.get('credit',0):,.0f}" if t.get('credit',0) > 0 else f"-â¹{t.get('debit',0):,.0f}"
            lines.append(f"  [{t.get('date','')}] {direction} | {str(t.get('description',''))[:60]} | [{t.get('category','Other')}]")

    lines.append("""
## Instructions

CAPABILITIES:
1. Answer questions about spending, income, savings, patterns
2. Identify top expenses, categories, trends
3. Generate charts using this EXACT format in your response:
   <chart>{"type":"bar","title":"...","labels":[...],"datasets":[{"label":"â¹ Amount","data":[...],"backgroundColor":["#6366f1","#10b981","#f59e0b","#ef4444","#3b82f6","#8b5cf6","#ec4899"]}]}</chart>

CHART TYPES:
- Bar chart: {"type":"bar","title":"...","labels":[...],"datasets":[{"label":"...","data":[...],"backgroundColor":[...]}]}
- Doughnut: {"type":"doughnut","title":"...","labels":[...],"datasets":[{"data":[...],"backgroundColor":[...]}]}
- Horizontal bar: {"type":"bar","indexAxis":"y","title":"...","labels":[...],"datasets":[{"label":"...","data":[...],"backgroundColor":[...]}]}
- Line chart: {"type":"line","title":"...","labels":[...],"datasets":[{"label":"...","data":[...],"borderColor":"#6366f1","tension":0.4}]}

RULES:
- Always use â¹ and Indian format. Use L for lakhs (â¹1,50,000 = â¹1.5L)
- Give a crisp 2-3 line answer then show charts
- For "overview" or "summary" requests â generate 3+ charts
- If asked for visuals, ALWAYS include at least one chart
- Surya and Uday = employees; Sujana = academy rent; P2P transfers = crypto
- The user runs SkillStack Academy (edtech) and an Escape Room Cafe in Visakhapatnam
- Be like a smart CFO who's also a friend â direct, warm, no fluff""")

    return "\n".join(lines)


# ââ Routes âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

@app.route('/')
def index():
    return send_from_directory(ROOT_DIR, 'index.html')


@app.route('/api/upload', methods=['POST'])
def upload():
    """Receive pre-extracted text from PDF.js on the client, parse with Claude."""
    data = request.get_json(force=True)
    api_key = data.get('api_key', '').strip()
    if not api_key:
        return jsonify({'error': 'API key required'}), 400

    files = data.get('files', [])
    if not files:
        return jsonify({'error': 'No files provided'}), 400

    results = []
    for f in files:
        filename = f.get('filename', 'statement.pdf')
        error = f.get('error', '')
        if error:
            results.append({'filename': filename, 'error': error})
            continue

        raw_text = f.get('text', '').strip()
        if not raw_text or len(raw_text) < 80:
            results.append({'filename': filename, 'error': f'PDF text extraction failed â only {len(raw_text)} chars extracted. PDF may be image-based or password may be wrong.'})
            continue

        try:
            parsed = parse_with_claude(raw_text, api_key, filename)
            parsed['filename'] = filename
            results.append(parsed)
        except Exception as e:
            results.append({'filename': filename, 'error': str(e)})

    return jsonify({'accounts': results})


@app.route('/api/chat', methods=['POST'])
def chat():
    """Stateless chat â client sends full context with each request, returns JSON."""
    data = request.get_json(force=True)
    user_message = data.get('message', '').strip()
    api_key = data.get('api_key', '').strip()
    accounts = data.get('accounts', [])
    history = data.get('history', [])

    if not api_key:
        return jsonify({'error': 'API key required'}), 400
    if not user_message:
        return jsonify({'error': 'Message required'}), 400
    if not accounts:
        return jsonify({'error': 'No bank statement data. Please upload statements first.'}), 400

    messages = list(history) + [{'role': 'user', 'content': user_message}]

    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=2048,
            system=build_system_prompt(accounts),
            messages=messages,
        )
        return jsonify({'response': msg.content[0].text})
    except anthropic.AuthenticationError:
        return jsonify({'error': 'Invalid API key.'}), 401
    except anthropic.RateLimitError:
        return jsonify({'error': 'Rate limit hit. Try again in a moment.'}), 429
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reset', methods=['POST'])
def reset():
    # Stateless â nothing to clear server-side
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    print('ð FinanceChat running on http://localhost:5050')
    app.run(debug=False, port=5050, host='0.0.0.0', threaded=True)
