import type { NextRequest } from "next/server"
import { kv } from "@vercel/kv"

const ADMIN_IDS = process.env.ADMIN_IDS ? process.env.ADMIN_IDS.split("6440962840,").map((id) => Number.parseInt(id)) : []

export async function POST(request: NextRequest) {
  try {
    const { userId, action, targetId, amount } = await request.json()

    // Verify admin
    if (!ADMIN_IDS.includes(userId)) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), { status: 401 })
    }

    switch (action) {
      case "add_credits":
        await addCredits(targetId, amount)
        return new Response(JSON.stringify({ success: true, message: `Added ${amount} credits to user ${targetId}` }))

      case "remove_credits":
        await removeCredits(targetId, amount)
        return new Response(
          JSON.stringify({ success: true, message: `Removed ${amount} credits from user ${targetId}` }),
        )

      case "give_premium":
        await givePremium(targetId, amount) // amount = days
        return new Response(
          JSON.stringify({ success: true, message: `Gave ${amount} days of premium to user ${targetId}` }),
        )

      case "revoke_premium":
        await revokePremium(targetId)
        return new Response(JSON.stringify({ success: true, message: `Revoked premium from user ${targetId}` }))

      case "get_stats":
        const stats = await getStats()
        return new Response(JSON.stringify({ success: true, stats }))

      default:
        return new Response(JSON.stringify({ error: "Invalid action" }), { status: 400 })
    }
  } catch (error) {
    console.error("Error in admin action:", error)
    return new Response(JSON.stringify({ error: "Internal server error" }), { status: 500 })
  }
}

async function addCredits(userId: number, amount: number) {
  const userData = await kv.get(`user:${userId}`)
  if (!userData) throw new Error("User not found")

  const user = JSON.parse(userData as string)
  user.credits += amount
  await kv.set(`user:${userId}`, JSON.stringify(user))
}

async function removeCredits(userId: number, amount: number) {
  const userData = await kv.get(`user:${userId}`)
  if (!userData) throw new Error("User not found")

  const user = JSON.parse(userData as string)
  user.credits = Math.max(0, user.credits - amount)
  await kv.set(`user:${userId}`, JSON.stringify(user))
}

async function givePremium(userId: number, days: number) {
  const userData = await kv.get(`user:${userId}`)
  if (!userData) throw new Error("User not found")

  const user = JSON.parse(userData as string)
  user.isPremium = true

  const now = Date.now()
  const expiryDate = now + days * 24 * 60 * 60 * 1000
  user.premiumExpiry = expiryDate

  await kv.set(`user:${userId}`, JSON.stringify(user))
}

async function revokePremium(userId: number) {
  const userData = await kv.get(`user:${userId}`)
  if (!userData) throw new Error("User not found")

  const user = JSON.parse(userData as string)
  user.isPremium = false
  user.premiumExpiry = undefined

  await kv.set(`user:${userId}`, JSON.stringify(user))
}

async function getStats() {
  // Get all users
  const userKeys = await kv.keys("user:*")
  const users = await Promise.all(userKeys.map((key) => kv.get(key)))

  // Calculate stats
  const totalUsers = users.length
  const premiumUsers = users.filter((user) => {
    const userData = JSON.parse(user as string)
    return userData.isPremium
  }).length

  const totalCredits = users.reduce((sum, user) => {
    const userData = JSON.parse(user as string)
    return sum + userData.credits
  }, 0)

  return {
    totalUsers,
    premiumUsers,
    totalCredits,
    averageCredits: totalUsers > 0 ? Math.floor(totalCredits / totalUsers) : 0,
  }
}

