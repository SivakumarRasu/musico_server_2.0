from fastapi import APIRouter, Request

router = APIRouter(
    tags=["Payment"]
)

@router.post("/webhook")
async def razorpay_webhook(request: Request):

    body = await request.body()

    signature = request.headers.get(
        "X-Razorpay-Signature"
    )

    payload = await request.json()

    event = payload["event"]

    if event == "payment.captured":

        payment_entity = payload["payload"]["payment"]["entity"]

        email = payment_entity["email"]

    return {"success": True,
            "email":email}