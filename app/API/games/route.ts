import type { NextRequest } from "next/server"
import { kv } from "@vercel/kv"

interface GameState {
  type: string
  status: "active" | "completed"
  credits: number
  data: any
}

export async function POST(request: NextRequest) {
  try {
    const { userId, gameType, action, data } = await request.json()

    // Get current game state
    const gameState: GameState | null = await kv.get(`game:${userId}`)

    // Handle different game types
    switch (gameType) {
      case "dice":
        return handleDiceGame(userId, action, gameState, data)
      case "number":
        return handleNumberGame(userId, action, gameState, data)
      case "quiz":
        return handleQuizGame(userId, action, gameState, data)
      default:
        return new Response(JSON.stringify({ error: "Invalid game type" }), { status: 400 })
    }
  } catch (error) {
    console.error("Error handling game action:", error)
    return new Response(JSON.stringify({ error: "Internal server error" }), { status: 500 })
  }
}

async function handleDiceGame(userId: string, action: string, gameState: GameState | null, data: any) {
  if (action === "start") {
    const newGame: GameState = {
      type: "dice",
      status: "active",
      credits: 10,
      data: {
        rolls: 0,
        target: Math.floor(Math.random() * 6) + 1,
      },
    }

    await kv.set(`game:${userId}`, JSON.stringify(newGame))
    return new Response(
      JSON.stringify({
        message: "Roll the dice! Try to match the target number.",
        target: newGame.data.target,
      }),
    )
  }

  if (action === "roll") {
    if (!gameState || gameState.type !== "dice") {
      return new Response(JSON.stringify({ error: "No active dice game" }), { status: 400 })
    }

    const roll = Math.floor(Math.random() * 6) + 1
    gameState.data.rolls++

    if (roll === gameState.data.target) {
      // Player wins
      const reward = gameState.credits * 2
      await updateUserCredits(userId, reward)
      await kv.del(`game:${userId}`)

      return new Response(
        JSON.stringify({
          message: `🎲 You rolled a ${roll}! You win ${reward} credits!`,
          won: true,
          reward,
        }),
      )
    }

    if (gameState.data.rolls >= 3) {
      // Game over
      await kv.del(`game:${userId}`)
      return new Response(
        JSON.stringify({
          message: `🎲 You rolled a ${roll}. Game over! You lost ${gameState.credits} credits.`,
          won: false,
        }),
      )
    }

    // Continue game
    await kv.set(`game:${userId}`, JSON.stringify(gameState))
    return new Response(
      JSON.stringify({
        message: `🎲 You rolled a ${roll}. Try again! ${3 - gameState.data.rolls} rolls left.`,
        won: false,
      }),
    )
  }

  return new Response(JSON.stringify({ error: "Invalid action" }), { status: 400 })
}

async function updateUserCredits(userId: string, amount: number) {
  const userData = await kv.get(`user:${userId}`)
  if (!userData) return

  const user = JSON.parse(userData as string)
  user.credits += amount
  await kv.set(`user:${userId}`, JSON.stringify(user))
}

async function handleNumberGame(userId: string, action: string, gameState: GameState | null, data: any) {
  return new Response(JSON.stringify({ error: "Number game not implemented" }), {
    status: 501,
  })
}

async function handleQuizGame(userId: string, action: string, gameState: GameState | null, data: any) {
  return new Response(JSON.stringify({ error: "Quiz game not implemented" }), {
    status: 501,
  })
}

