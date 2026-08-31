import { useState } from 'react'
import { useData } from './hooks/useData.js'
import { shuffle } from './utils/helpers.js'
import HomeScreen from './components/HomeScreen.jsx'
import FlashCard from './components/FlashCard.jsx'
import SessionEnd from './components/SessionEnd.jsx'
import './styles/App.css'

// Screens: 'home' | 'session' | 'end'
export default function App() {
  const { cards, decks, faq, cardMap, loading, error } = useData()
  const [screen, setScreen]         = useState('home')
  const [sessionCards, setSession]  = useState([])
  const [sessionIndex, setIndex]    = useState(0)
  const [sessionMeta, setMeta]      = useState(null) // { mode, deckName }

  if (loading) return <LoadingScreen />
  if (error)   return <ErrorScreen message={error} />

  function handleStart({ mode, cards: pool, deck, card }) {
    let cardList = []
    let deckName = null

    if (mode === 'random') {
      cardList = shuffle(pool)
    } else if (mode === 'deck') {
      // The leader is part of the deck you're studying, so it belongs in the
      // pool too. It isn't in deck.cards (stored separately), hence the concat.
      const ids = deck.leader ? [deck.leader, ...deck.cards] : deck.cards
      cardList = shuffle(
        [...new Set(ids)]
          .map(id => cardMap[id])
          .filter(Boolean)
      )
      deckName = deck.name
    } else if (mode === 'lookup') {
      cardList = [card]
    }

    if (cardList.length === 0) return
    setSession(cardList)
    setIndex(0)
    setMeta({ mode, deckName })
    setScreen('session')
  }

  function handleNext() {
    if (sessionIndex + 1 >= sessionCards.length) {
      setScreen('end')
    } else {
      setIndex(i => i + 1)
    }
  }

  function handleRestart() {
    setSession(s => shuffle([...s]))
    setIndex(0)
    setScreen('session')
  }

  function handleHome() {
    setScreen('home')
    setSession([])
    setIndex(0)
    setMeta(null)
  }

  if (screen === 'home') {
    if (cards.length === 0) {
      return <EmptyDatabase />
    }
    return <HomeScreen decks={decks} cards={cards} cardMap={cardMap} faq={faq} onStart={handleStart} />
  }

  if (screen === 'session') {
    return (
      <FlashCard
        key={sessionIndex}
        card={sessionCards[sessionIndex]}
        faqEntries={faq[sessionCards[sessionIndex].id] || []}
        lookup={sessionMeta?.mode === 'lookup'}
        current={sessionIndex + 1}
        total={sessionCards.length}
        onNext={handleNext}
        onHome={handleHome}
      />
    )
  }

  if (screen === 'end') {
    return (
      <SessionEnd
        total={sessionCards.length}
        deckName={sessionMeta?.deckName}
        onRestart={handleRestart}
        onHome={handleHome}
      />
    )
  }
}

function LoadingScreen() {
  return (
    <div className="loading-screen">
      <div className="loading-spinner" />
      <p className="loading-text">Loading card data…</p>
    </div>
  )
}

function EmptyDatabase() {
  return (
    <div className="error-screen">
      <span className="error-icon">🗂️</span>
      <p className="error-text" style={{ textAlign: 'center' }}>
        No cards in the database yet.<br />
        Run the script to add cards:
      </p>
      <code style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '0.75rem',
        color: 'var(--gold)',
        background: 'var(--surface)',
        padding: '0.5rem 1rem',
        borderRadius: '6px',
        border: '1px solid var(--border)',
        marginTop: '0.5rem',
      }}>
        python scripts/add_cards.py --set OP01
      </code>
    </div>
  )
}

function ErrorScreen({ message }) {
  return (
    <div className="error-screen">
      <span className="error-icon">⚠️</span>
      <p className="error-text">Failed to load: {message}</p>
      <button onClick={() => window.location.reload()} className="error-reload">
        Reload
      </button>
    </div>
  )
}
