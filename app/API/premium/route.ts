import type { NextRequest } from "next/server"
import { kv } from "@vercel/kv"
import Stripe from "stripe"

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: "2023-10-16",
})

export async function POST(request: NextRequest) {
  try {
    const { userId, plan } = await request.json()

    const prices = {
      monthly: "price_monthly_id", // Replace with actual Stripe price IDs
      yearly: "price_yearly_id",
    }

    const session = await stripe.checkout.sessions.create({
      payment_method_types: ["card"],
      line_items: [
        {
          price: prices[plan as keyof typeof prices],
          quantity: 1,
        },
      ],
      mode: "subscription",
      success_url: `${process.env.NEXT_PUBLIC_URL}/premium/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${process.env.NEXT_PUBLIC_URL}/premium/cancel`,
      client_reference_id: userId,
    })

    return new Response(JSON.stringify({ url: session.url }))
  } catch (error) {
    console.error("Error creating premium subscription:", error)
    return new Response(JSON.stringify({ error: "Failed to create subscription" }), { status: 500 })
  }
}

export async function PUT(request: NextRequest) {
  try {
    const { userId, sessionId } = await request.json()

    const session = await stripe.checkout.sessions.retrieve(sessionId)
    if (session.payment_status !== "paid") {
      return new Response(JSON.stringify({ error: "Payment not completed" }), { status: 400 })
    }

    // Update user's premium status
    const userData = await kv.get(`user:${userId}`)
    if (!userData) {
      return new Response(JSON.stringify({ error: "User not found" }), { status: 404 })
    }

    const user = JSON.parse(userData as string)
    user.isPremium = true
    user.premiumExpiry = Date.now() + (session.mode === "subscription" ? 30 : 365) * 24 * 60 * 60 * 1000

    await kv.set(`user:${userId}`, JSON.stringify(user))

    return new Response(
      JSON.stringify({
        message: "Premium subscription activated",
        expiryDate: new Date(user.premiumExpiry).toISOString(),
      }),
    )
  } catch (error) {
    console.error("Error activating premium:", error)
    return new Response(JSON.stringify({ error: "Failed to activate premium" }), { status: 500 })
  }
}

