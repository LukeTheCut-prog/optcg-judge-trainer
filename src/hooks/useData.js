import { useState, useEffect } from 'react'

const BASE = import.meta.env.BASE_URL

function fixImageUrl(url) {
  // Local paths like /images/cards/OP01-001.png need the base prepended
  if (url && url.startsWith('/images/')) {
    return BASE + url.slice(1) // remove leading slash, BASE already has trailing slash
  }
  return url
}

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
        // Fix image URLs for GitHub Pages subdirectory hosting
        const fixedCards = cardsData.map(c => ({
          ...c,
          image_url: fixImageUrl(c.image_url)
        }))
        setCards(fixedCards)
        setDecks(decksData)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const cardMap = Object.fromEntries(cards.map(c => [c.id, c]))

  return { cards, decks, cardMap, loading, error }
}
