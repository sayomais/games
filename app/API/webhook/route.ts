import type { NextRequest } from "next/server"
import { kv } from "@vercel/kv"

const TELEGRAM_TOKEN = process.env.TELEGRAM_BOT_TOKEN
const ADMIN_IDS = process.env.ADMIN_IDS ? process.env.ADMIN_IDS.split(",").map((id) => Number.parseInt(id)) : []

interface User {
  id: number
  credits: number
  isPremium: boolean
  premiumExpiry?: number
  username: string
}

async function sendMessage(chatId: number, text: string, keyboard?: any) {
  const response = await fetch(`https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      reply_markup: keyboard,
      parse_mode: "HTML",
    }),
  })
  return response.json()
}

async function handleStart(chatId: number, username: string) {
  const user: User = {
    id: chatId,
    credits: 100, // Starting credits
    isPremium: false,
    username,
  }

  await kv.set(`user:${chatId}`, JSON.stringify(user))

  const welcomeMessage = `
🎮 Welcome to the Game Bot!

You have been given 100 credits to start.
Use /help to see available commands.

💎 Premium Features:
- Double credits rewards
- Exclusive games
- No daily limits
- Priority support

Contact an admin to get Premium status!
`

  const keyboard = {
    inline_keyboard: [
      [{ text: "🎮 Play Games", callback_data: "games" }],
      [{ text: "💰 Check Credits", callback_data: "credits" }],
    ],
  }

  await sendMessage(chatId, welcomeMessage, keyboard)
}

async function handleAdmin(chatId: number, command: string, args: string[]) {
  // Check if user is admin
  if (!ADMIN_IDS.includes(chatId)) {
    await sendMessage(chatId, "⚠️ You are not authorized to use admin commands.")
    return
  }

  const [targetUsername, ...rest] = args
  if (!targetUsername) {
    await sendMessage(chatId, "⚠️ Please specify a username.")
    return
  }

  // Get user by username
  const userKeys = await kv.keys("user:*")
  const users = await Promise.all(userKeys.map((key) => kv.get(key)))
  const targetUser = users.find((user) => {
    const userData = JSON.parse(user as string) as User
    return userData.username === targetUsername.replace("@", "")
  })

  if (!targetUser) {
    await sendMessage(chatId, `⚠️ User ${targetUsername} not found.`)
    return
  }

  const user = JSON.parse(targetUser as string) as User

  switch (command) {
    case "/givepremium":
      const days = Number.parseInt(rest[0]) || 30 // Default to 30 days if not specified
      user.isPremium = true
      user.premiumExpiry = Date.now() + days * 24 * 60 * 60 * 1000
      await kv.set(`user:${user.id}`, JSON.stringify(user))

      await sendMessage(chatId, `✅ Gave ${days} days of premium to @${user.username}`)
      await sendMessage(user.id, `🎉 You have been given ${days} days of premium status by an admin!`)
      break

    case "/revokepremium":
      user.isPremium = false
      user.premiumExpiry = undefined
      await kv.set(`user:${user.id}`, JSON.stringify(user))

      await sendMessage(chatId, `✅ Revoked premium from @${user.username}`)
      await sendMessage(user.id, "⚠️ Your premium status has been revoked by an admin.")
      break

    case "/addcredits":
      const amount = Number.parseInt(rest[0])
      if (isNaN(amount)) {
        await sendMessage(chatId, "⚠️ Please specify a valid amount of credits.")
        return
      }

      user.credits += amount
      await kv.set(`user:${user.id}`, JSON.stringify(user))

      await sendMessage(chatId, `✅ Added ${amount} credits to @${user.username}`)
      await sendMessage(user.id, `🎉 You have been given ${amount} credits by an admin!`)
      break

    case "/stats":
      const stats = {
        totalUsers: users.length,
        premiumUsers: users.filter((u) => {
          const userData = JSON.parse(u as string) as User
          return userData.isPremium
        }).length,
        totalCredits: users.reduce((sum, u) => {
          const userData = JSON.parse(u as string) as User
          return sum + userData.credits
        }, 0),
      }

      await sendMessage(
        chatId,
        `📊 Bot Statistics

Total Users: ${stats.totalUsers}
Premium Users: ${stats.premiumUsers}
Total Credits: ${stats.totalCredits}
Average Credits: ${Math.floor(stats.totalCredits / stats.totalUsers)}`,
      )
      break

    default:
      await sendMessage(chatId, "⚠️ Unknown admin command.")
  }
}

async function handleHelp(chatId: number) {
  const isAdmin = ADMIN_IDS.includes(chatId)

  let helpMessage = `
📚 Game Bot Commands

Basic Commands:
/start - Initialize the bot
/games - Show available games
/credits - Check your credit balance
/daily - Claim daily reward
/help - Show this help message

Game Commands:
/dice - Roll the dice game
/number - Number guessing game
/quiz - Trivia quiz game

Premium users also have access to:
/blackjack - Play Blackjack
/poker - Play Poker
/slots - Premium Slots`

  if (isAdmin) {
    helpMessage += `

🔑 Admin Commands:
/givepremium @username [days] - Give premium status
/revokepremium @username - Revoke premium status
/addcredits @username [amount] - Add credits
/stats - View bot statistics`
  }

  await sendMessage(chatId, helpMessage)
}

async function handleCredits(chatId: number) {
  const userData = await kv.get(`user:${chatId}`)
  if (!userData) {
    await sendMessage(chatId, "Error: User not found. Please use /start to register.")
    return
  }

  const user: User = JSON.parse(userData as string)
  const premiumStatus = user.isPremium ? "💎 Premium" : "Free"
  const premiumExpiry = user.premiumExpiry
    ? `\nPremium expires: ${new Date(user.premiumExpiry).toLocaleDateString()}`
    : ""

  const message = `
💰 Your Credits: ${user.credits}
🎯 Status: ${premiumStatus}${premiumExpiry}

Daily Rewards:
- Free users: 50 credits
- Premium users: 100 credits

Use /play to start earning more credits!
`

  const keyboard = {
    inline_keyboard: [
      [{ text: "🎮 Play Games", callback_data: "games" }],
      [{ text: "💰 Check Credits", callback_data: "credits" }],
      [{ text: "🔙 Back to Menu", callback_data: "menu" }],
    ],
  }

  await sendMessage(chatId, message, keyboard)
}

async function handleGames(chatId: number) {
  const userData = await kv.get(`user:${chatId}`)
  if (!userData) {
    await sendMessage(chatId, "Error: User not found. Please use /start to register.")
    return
  }

  const user: User = JSON.parse(userData as string)
  const premiumGames = user.isPremium
    ? `
🎯 Premium Games:
/blackjack - Play Blackjack
/poker - Play Poker
/slots - Premium Slots`
    : ""

  const message = `
🎮 Available Games:

Free Games:
/dice - Roll the dice
/number - Guess the number
/quiz - Play trivia quiz
${premiumGames}

💰 Your Credits: ${user.credits}
`

  const keyboard = {
    inline_keyboard: [
      [{ text: "🎲 Roll Dice", callback_data: "play_dice" }],
      [{ text: "🔢 Number Game", callback_data: "play_number" }],
      [{ text: "❓ Quiz Game", callback_data: "play_quiz" }],
      [{ text: "🔙 Back to Menu", callback_data: "menu" }],
    ],
  }

  await sendMessage(chatId, message, keyboard)
}

async function handleMenu(chatId: number) {
  const keyboard = {
    inline_keyboard: [
      [{ text: "🎮 Play Games", callback_data: "games" }],
      [{ text: "💎 Get Premium", callback_data: "premium" }],
      [{ text: "💰 Check Credits", callback_data: "credits" }],
      [{ text: "ℹ️ Help", callback_data: "help" }],
    ],
  }

  await sendMessage(chatId, "🎮 Game Bot - Main Menu", keyboard)
}

async function handleDaily(chatId: number) {
  const userData = await kv.get(`user:${chatId}`)
  if (!userData) {
    await sendMessage(chatId, "Error: User not found. Please use /start to register.")
    return
  }

  const user: User = JSON.parse(userData as string)

  // Check if user has claimed daily reward today
  const lastClaimKey = `daily:${chatId}`
  const lastClaim = await kv.get(lastClaimKey)

  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()

  if (lastClaim && Number(lastClaim) >= today) {
    await sendMessage(chatId, "You've already claimed your daily reward today. Come back tomorrow!", {
      inline_keyboard: [[{ text: "🔙 Back to Menu", callback_data: "menu" }]],
    })
    return
  }

  // Give daily reward based on premium status
  const reward = user.isPremium ? 100 : 50
  user.credits += reward

  // Update user data and last claim
  await kv.set(`user:${chatId}`, JSON.stringify(user))
  await kv.set(lastClaimKey, today)

  await sendMessage(
    chatId,
    `✅ Daily reward claimed!

You received ${reward} credits.
Current balance: ${user.credits} credits.

${user.isPremium ? "💎 Premium bonus applied!" : "💡 Tip: Premium users get double daily rewards!"}`,
    {
      inline_keyboard: [
        [{ text: "🎮 Play Games", callback_data: "games" }],
        [{ text: "🔙 Back to Menu", callback_data: "menu" }],
      ],
    },
  )
}

export async function POST(request: NextRequest) {
  try {
    const update = await request.json()

    // Handle messages
    if (update.message) {
      const chatId = update.message.chat.id
      const text = update.message.text
      const username = update.message.from.username

      // Handle admin commands
      if (text?.startsWith("/") && ADMIN_IDS.includes(chatId)) {
        const [command, ...args] = text.split(" ")
        if (["/givepremium", "/revokepremium", "/addcredits", "/stats"].includes(command)) {
          await handleAdmin(chatId, command, args)
          return new Response("OK")
        }
      }

      // Handle regular commands
      switch (text) {
        case "/start":
          await handleStart(chatId, username)
          break
        case "/help":
          await handleHelp(chatId)
          break
        case "/premium":
          //await handlePremium(chatId)
          break
        case "/credits":
          await handleCredits(chatId)
          break
        case "/games":
          await handleGames(chatId)
          break
        case "/daily":
          await handleDaily(chatId)
          break
        case "/dice":
          await startGame(chatId, "dice")
          break
        case "/number":
          await startGame(chatId, "number")
          break
        case "/quiz":
          await startGame(chatId, "quiz")
          break
        case "/blackjack":
        case "/poker":
        case "/slots":
          await handlePremiumGame(chatId, text.substring(1))
          break
        default:
          // Check if this is a game response
          await handleGameResponse(chatId, text)
      }
    }

    // Handle callback queries (button clicks)
    if (update.callback_query) {
      const chatId = update.callback_query.from.id
      const data = update.callback_query.data

      switch (data) {
        case "games":
          await handleGames(chatId)
          break
        case "premium":
          //await handlePremium(chatId)
          break
        case "credits":
          await handleCredits(chatId)
          break
        case "menu":
          await handleMenu(chatId)
          break
        case "help":
          await handleHelp(chatId)
          break
        case "premium_1day":
          //await handlePurchasePremium(chatId, 1)
          break
        case "premium_7days":
          //await handlePurchasePremium(chatId, 7)
          break
        case "premium_30days":
          //await handlePurchasePremium(chatId, 30)
          break
        case "play_dice":
          await startGame(chatId, "dice")
          break
        case "play_number":
          await startGame(chatId, "number")
          break
        case "play_quiz":
          await startGame(chatId, "quiz")
          break
      }

      return new Response("OK")
    }

    return new Response("OK")
  } catch (error) {
    console.error("Error handling webhook:", error)
    return new Response("Error", { status: 500 })
  }
}

async function startGame(chatId: number, gameType: string) {
  const userData = await kv.get(`user:${chatId}`)
  if (!userData) {
    await sendMessage(chatId, "Error: User not found. Please use /start to register.")
    return
  }

  const user: User = JSON.parse(userData as string)

  // Check if user has enough credits to play
  const gameCost = 10
  if (user.credits < gameCost) {
    await sendMessage(chatId, `You don't have enough credits to play. You need ${gameCost} credits.`, {
      inline_keyboard: [
        [{ text: "💰 Claim Daily Reward", callback_data: "daily" }],
        [{ text: "🔙 Back to Menu", callback_data: "menu" }],
      ],
    })
    return
  }

  // Deduct credits
  user.credits -= gameCost
  await kv.set(`user:${chatId}`, JSON.stringify(user))

  // Start the game based on type
  switch (gameType) {
    case "dice":
      const target = Math.floor(Math.random() * 6) + 1
      await kv.set(
        `game:${chatId}`,
        JSON.stringify({
          type: "dice",
          target,
          attempts: 0,
          cost: gameCost,
        }),
      )

      await sendMessage(
        chatId,
        `🎲 Dice Game Started!

I'm thinking of a number between 1 and 6.
You have 3 attempts to guess it.
Cost: ${gameCost} credits

Type a number between 1 and 6 to guess:`,
        {
          inline_keyboard: [
            [
              { text: "1", callback_data: "guess_1" },
              { text: "2", callback_data: "guess_2" },
              { text: "3", callback_data: "guess_3" },
              { text: "4", callback_data: "guess_4" },
              { text: "5", callback_data: "guess_5" },
              { text: "6", callback_data: "guess_6" },
            ],
          ],
        },
      )
      break

    case "number":
      const secretNumber = Math.floor(Math.random() * 100) + 1
      await kv.set(
        `game:${chatId}`,
        JSON.stringify({
          type: "number",
          number: secretNumber,
          attempts: 0,
          maxAttempts: 5,
          cost: gameCost,
        }),
      )

      await sendMessage(
        chatId,
        `🔢 Number Guessing Game Started!

I'm thinking of a number between 1 and 100.
You have 5 attempts to guess it.
Cost: ${gameCost} credits

Type a number between 1 and 100 to guess:`,
      )
      break

    case "quiz":
      // Simple quiz implementation
      const questions = [
        {
          question: "What is the capital of France?",
          options: ["London", "Berlin", "Paris", "Madrid"],
          answer: 2, // Paris
        },
        {
          question: "Which planet is known as the Red Planet?",
          options: ["Venus", "Mars", "Jupiter", "Saturn"],
          answer: 1, // Mars
        },
        {
          question: "What is 2 + 2?",
          options: ["3", "4", "5", "22"],
          answer: 1, // 4
        },
      ]

      const randomQuestion = questions[Math.floor(Math.random() * questions.length)]

      await kv.set(
        `game:${chatId}`,
        JSON.stringify({
          type: "quiz",
          question: randomQuestion.question,
          options: randomQuestion.options,
          answer: randomQuestion.answer,
          cost: gameCost,
        }),
      )

      const optionsKeyboard = {
        inline_keyboard: randomQuestion.options.map((option, index) => {
          return [{ text: option, callback_data: `answer_${index}` }]
        }),
      }

      await sendMessage(
        chatId,
        `❓ Quiz Game Started!

${randomQuestion.question}
Cost: ${gameCost} credits

Select your answer:`,
        optionsKeyboard,
      )
      break
  }
}

async function handleGameResponse(chatId: number, text: string) {
  const gameData = await kv.get(`game:${chatId}`)
  if (!gameData) {
    // No active game
    return
  }

  const game = JSON.parse(gameData as string)

  switch (game.type) {
    case "dice":
      const guess = Number.parseInt(text)
      if (isNaN(guess) || guess < 1 || guess > 6) {
        await sendMessage(chatId, "Please enter a number between 1 and 6.")
        return
      }

      game.attempts++

      if (guess === game.target) {
        // Win
        const reward = game.cost * 3
        await updateUserCredits(chatId, reward)
        await kv.del(`game:${chatId}`)

        await sendMessage(
          chatId,
          `🎉 Congratulations! You guessed correctly: ${guess}
          
You won ${reward} credits!`,
          {
            inline_keyboard: [
              [{ text: "🎮 Play Again", callback_data: "play_dice" }],
              [{ text: "🔙 Back to Games", callback_data: "games" }],
            ],
          },
        )
      } else if (game.attempts >= 3) {
        // Game over
        await kv.del(`game:${chatId}`)

        await sendMessage(
          chatId,
          `Game Over! You've used all your attempts.
The correct number was ${game.target}.

You lost ${game.cost} credits.`,
          {
            inline_keyboard: [
              [{ text: "🎮 Try Again", callback_data: "play_dice" }],
              [{ text: "🔙 Back to Games", callback_data: "games" }],
            ],
          },
        )
      } else {
        // Continue
        await kv.set(`game:${chatId}`, JSON.stringify(game))

        await sendMessage(
          chatId,
          `Wrong guess! The number is ${guess < game.target ? "higher" : "lower"} than ${guess}.
          
Attempts left: ${3 - game.attempts}
          
Try again with a number between 1 and 6:`,
          {
            inline_keyboard: [
              [
                { text: "1", callback_data: "guess_1" },
                { text: "2", callback_data: "guess_2" },
                { text: "3", callback_data: "guess_3" },
                { text: "4", callback_data: "guess_4" },
                { text: "5", callback_data: "guess_5" },
                { text: "6", callback_data: "guess_6" },
              ],
            ],
          },
        )
      }
      break

    case "number":
      // Similar implementation for number game
      break
  }
}

async function handlePremiumGame(chatId: number, gameType: string) {
  const userData = await kv.get(`user:${chatId}`)
  if (!userData) {
    await sendMessage(chatId, "Error: User not found. Please use /start to register.")
    return
  }

  const user: User = JSON.parse(userData as string)

  // Check if user is premium
  if (!user.isPremium) {
    await sendMessage(
      chatId,
      `⭐ This is a premium game!

You need to be a premium user to play ${gameType}.`,
      {
        inline_keyboard: [
          [{ text: "💎 Get Premium", callback_data: "premium" }],
          [{ text: "🔙 Back to Games", callback_data: "games" }],
        ],
      },
    )
    return
  }

  // Check if premium expired
  if (user.premiumExpiry && user.premiumExpiry < Date.now()) {
    user.isPremium = false
    await kv.set(`user:${chatId}`, JSON.stringify(user))

    await sendMessage(
      chatId,
      `⚠️ Your premium subscription has expired!

You need to renew your premium status to play ${gameType}.`,
      {
        inline_keyboard: [
          [{ text: "💎 Renew Premium", callback_data: "premium" }],
          [{ text: "🔙 Back to Games", callback_data: "games" }],
        ],
      },
    )
    return
  }

  // Start premium game
  switch (gameType) {
    case "blackjack":
      await sendMessage(
        chatId,
        `♠️ Blackjack Game

Premium game coming soon!
Check back later for this exclusive game.`,
        {
          inline_keyboard: [[{ text: "🔙 Back to Games", callback_data: "games" }]],
        },
      )
      break

    case "poker":
      await sendMessage(
        chatId,
        `♦️ Poker Game

Premium game coming soon!
Check back later for this exclusive game.`,
        {
          inline_keyboard: [[{ text: "🔙 Back to Games", callback_data: "games" }]],
        },
      )
      break

    case "slots":
      // Simple slots implementation
      const symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
      const result = [
        symbols[Math.floor(Math.random() * symbols.length)],
        symbols[Math.floor(Math.random() * symbols.length)],
        symbols[Math.floor(Math.random() * symbols.length)],
      ]

      // Calculate winnings
      let winnings = 0
      const bet = 50

      if (result[0] === result[1] && result[1] === result[2]) {
        // All three match - big win
        winnings = bet * 10
        if (result[0] === "💎") winnings = bet * 20
        if (result[0] === "7️⃣") winnings = bet * 50
      } else if (result[0] === result[1] || result[1] === result[2] || result[0] === result[2]) {
        // Two match - small win
        winnings = bet * 2
      }

      // Update credits
      if (winnings > 0) {
        await updateUserCredits(chatId, winnings)
      } else {
        await updateUserCredits(chatId, -bet)
      }

      await sendMessage(
        chatId,
        `🎰 Premium Slots

${result.join(" | ")}

${winnings > 0 ? `🎉 You won ${winnings} credits!` : `😢 You lost ${bet} credits.`}`,
        {
          inline_keyboard: [
            [{ text: "🎰 Spin Again", callback_data: "play_slots" }],
            [{ text: "🔙 Back to Games", callback_data: "games" }],
          ],
        },
      )
      break
  }
}

async function updateUserCredits(userId: number, amount: number) {
  const userData = await kv.get(`user:${userId}`)
  if (!userData) return

  const user = JSON.parse(userData as string)
  user.credits += amount
  if (user.credits < 0) user.credits = 0
  await kv.set(`user:${userId}`, JSON.stringify(user))
}

