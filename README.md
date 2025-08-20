## 24/7 AI Merch Automation (Zero fixed cost MVP)

This MVP:

- Watches Twitch chat for opted-in channels and detects hot phrases in real time
- Generates vector merch designs (SVG) and PNG exports
- Serves a simple storefront with Stripe Checkout for digital downloads


Run locally:

```bash
npm install
npm run dev
```

Configure channels in `config/channels.yaml` with `twitchChannels`.

Env (optional for checkout): `STRIPE_SECRET_KEY`, `SITE_URL`, `DOWNLOAD_SECRET`.

Storefront at `http://localhost:8787`. Designs under `assets/designs/`.