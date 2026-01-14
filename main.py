import os, time
from urllib.parse import urlencode
import stripe
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# --- CONFIG ---
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
CARE_LINK_BASE = os.getenv("CARE_LINK_BASE")
SUCCESS_URL = os.getenv("SUCCESS_URL")
CANCEL_URL = os.getenv("CANCEL_URL")
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")

PRICE_ID_MAP = {
    149: os.getenv("PRICE_ID_149"),
    249: os.getenv("PRICE_ID_249"),
    349: os.getenv("PRICE_ID_349"),
    495: os.getenv("PRICE_ID_495"),
}

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CREATE CHECKOUT ---
@app.post("/create-checkout")
async def create_checkout(payload: dict):
    tier = int(payload["tier"])
    price_id = PRICE_ID_MAP.get(tier)
    if not price_id:
        raise HTTPException(400, "Invalid tier")

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=SUCCESS_URL,
        cancel_url=CANCEL_URL,
        metadata={"tier": tier},
    )
    return {"checkout_url": session.url}

# --- STRIPE WEBHOOK ---
@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        tier = session["metadata"]["tier"]

        params = urlencode({"tier": tier})
        redirect = f"{CARE_LINK_BASE}&{params}"
        return {"redirect": redirect}

    return {"status": "ok"}

# --- POST-PAY REDIRECT ---
@app.get("/next")
def postpay_next(tier: int):
    return {
        "next_url": f"{CARE_LINK_BASE}&tier={tier}"
    }
