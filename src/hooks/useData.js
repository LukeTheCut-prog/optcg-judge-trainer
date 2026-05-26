import { useState, useEffect } from 'react'

const BASE = import.meta.env.BASE_URL

export function useData() {
  const [cards, setCards]   = useState([])
  const [decks, setDecks]   = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  useEffect(() => {
    async function load() {
      try {
        const [cardsRes, decksRes] = await Promise.all([
          fetch(`${BASE}data/cards.json`),
          fetch(`${BASE}data/decks.json`),
        ])
        if (!cardsRes.ok || !decksRes.ok) throw new Error('Failed to load data')
        const [cardsData, decksData] = await Promise.all([
          cardsRes.json(),
          decksRes.json(),
        ])
        setCards(cardsData)
        setDecks(decksData)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Build a card lookup map for fast access
  const cardMap = Object.fromEntries(cards.map(c => [c.id, c]))

  return { cards, decks, cardMap, loading, error }
}
