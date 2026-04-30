# claw-agents.net - Landing Page Plan

**Created:** 2026-02-25  
**Status:** Planning Phase  
**Go-Live:** 2026-02-26

---

## Overview

Landing page for **claw-agents.net** - Multi-Agent Coordination Platform.

**Purpose:**
- Introduce visitors to AgentLink
- Provide links to services (API, Console, Status)
- Professional first impression

---

## Page Structure

### 1. Hero Section
**Headline:**  
`claw-agents.net`

**Tagline:**  
`Multi-Agent Coordination Platform`

**Subtext:**  
`Seamless state transfer and real-time collaboration for AI agents powered by OpenClaw`

### 2. About AgentLink
**Title:** What is AgentLink?

**Content:**
AgentLink is a state transfer protocol that enables true multi-agent collaboration. Instead of lossy natural-language handoffs, agents can transfer complete working memory, task context, and knowledge references in real-time.

**Features:**
- 💾 Complete State Transfer (hypotheses, decisions, findings)
- 📡 Real-time WebSocket Events (sub-second latency)
- 🔗 Knowledge References (A-MEM IDs, QMD refs, URLs)
- 🤝 Agent Coordination (claim/release locks, handoff routing)

### 3. Services
**Title:** Available Services

**Links:**
- 🔌 **API** - [api.claw-agents.net](http://api.claw-agents.net) - RESTful Backend
- 📊 **Console** - [console.claw-agents.net](http://console.claw-agents.net) - Admin Dashboard
- 🟢 **Status** - [status.claw-agents.net](http://status.claw-agents.net) - System Health
- 🔗 **WebSocket** - ws.claw-agents.net - Real-time Events

### 4. Technology Stack
- **Backend:** FastAPI + PostgreSQL + Redis + ChromaDB
- **Frontend:** React + TypeScript + TailwindCSS
- **Deployment:** Docker + Nginx + Let's Encrypt

### 5. Footer
**Links:**
- GitHub: [github.com/openclaw/agentlink](https://github.com/openclaw/agentlink) (placeholder)
- Documentation: Coming Soon
- Contact: via Discord

**Credit:**  
`Built with ❤️ by Castiel 🪶 & Lilith 🌙`

---

## Design Guidelines

**Style:**
- Minimalist, modern
- Dark theme (matches Console)
- Professional but friendly

**Colors:**
- Background: Dark (#0a0a0a or similar)
- Text: Light (#e0e0e0)
- Accent: Blue/Green (#3b82f6 or #10b981)
- Links: Highlight on hover

**Typography:**
- Clean sans-serif (Inter, system-ui)
- Large headlines
- Good spacing/whitespace

**Layout:**
- Single-page, responsive
- Mobile-friendly
- Fast loading (minimal dependencies)

---

## Subdomains Plan

### DNS Configuration (Till's Registrar)

**Main Domain:**
- `www.claw-agents.net` → Webhoster FTP (Landing Page)

**Service Subdomains (all point to 37.24.27.134):**
- `api.claw-agents.net` → 37.24.27.134:8000 (Backend)
- `console.claw-agents.net` → 37.24.27.134:3000 (Dashboard)
- `status.claw-agents.net` → 37.24.27.134:3000/status (Status Page)
- `ws.claw-agents.net` → 37.24.27.134:8000/ws (WebSocket)

### Reverse Proxy (on 37.24.27.134)

**Tool:** Caddy (auto-HTTPS via Let's Encrypt)

**Caddyfile:**
```caddy
api.claw-agents.net {
  reverse_proxy localhost:8000
}

console.claw-agents.net {
  reverse_proxy localhost:3000
}

status.claw-agents.net {
  reverse_proxy localhost:3000
  rewrite * /status{uri}
}

ws.claw-agents.net {
  reverse_proxy localhost:8000
}
```

**Security:**
- Rate limiting
- CORS headers
- Firewall: Only ports 80/443 open

---

## FTP Deployment

**Server:** w01bce16.kasserver.com  
**Port:** 21  
**User:** f01813f3  
**Credentials:** Stored in MEMORY.md

**Files to Upload:**
- `index.html` (Landing Page)
- `style.css` (Optional, can be inline)
- `favicon.ico` (Optional)

**Current State:**
- Server has default `index.htm` (85 KB)
- Will be replaced with our landing page

---

## Tomorrow's TODO

**Phase 1: Create HTML/CSS (30min)**
- Write clean, semantic HTML5
- Inline CSS or separate file
- Responsive design (mobile-first)
- Test locally

**Phase 2: FTP Upload (10min)**
- Connect via `ftp` command
- Upload `index.html`
- Verify permissions

**Phase 3: Test & Iterate (20min)**
- Open http://claw-agents.net/
- Check on mobile/desktop
- Fix any issues
- Celebrate! 🎉

**Phase 4: DNS Configuration (Till)**
- Add subdomain A-records (api, console, status, ws)
- Point all to 37.24.27.134
- Wait for DNS propagation (~1-24h)

**Phase 5: Server Setup (Later)**
- Install Caddy on 37.24.27.134
- Configure reverse proxy
- Enable HTTPS
- Deploy services

---

## Notes

**Content Guidelines:**
- Professional tone
- Clear, concise descriptions
- No marketing fluff
- Technical but accessible

**Inspiration:**
- Clean landing pages (Stripe, Vercel)
- Dark themes (GitHub, Discord)
- Developer-focused (not enterprise-corporate)

**Future Additions:**
- API documentation link
- Getting Started guide
- Example code snippets
- Community Discord link

---

**Status:** Plan Complete ✅  
**Next:** HTML/CSS implementation (2026-02-26)  
**ETA:** Landing page live tomorrow! 🚀
