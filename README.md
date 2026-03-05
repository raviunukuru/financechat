# 💹 FinanceChat

AI-powered bank statement analyser. Upload any month's PDFs, chat with Claude, get instant charts and insights.

## Features
- 📂 Drag & drop PDF upload — passwords auto-read from filename like `HDFC (123456).pdf`
- 🤖 Claude Haiku parses every transaction instantly
- 💬 Chat with Claude Sonnet about your money
- 📊 Inline charts auto-generated in chat (bar, doughnut, horizontal, line)
- 🔒 Stateless — your data never leaves the session

## Run Locally

```bash
chmod +x start.sh && ./start.sh
```
Then open http://localhost:5050

## Deploy to Vercel

1. Push this folder to a GitHub repo
2. Go to [vercel.com](https://vercel.com) → **New Project** → import the repo
3. Vercel auto-detects Python — just click **Deploy**
4. Done ✅

## Tech Stack
- **Backend**: Python + Flask (stateless, Vercel serverless)
- **AI**: Anthropic Claude Haiku (parsing) + Sonnet (chat + charts)
- **Frontend**: Vanilla JS + Chart.js 4 — zero framework
