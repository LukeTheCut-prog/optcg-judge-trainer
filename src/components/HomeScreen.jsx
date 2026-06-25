import { useState, useMemo } from 'react'
import './HomeScreen.css'

// Standard format: OP05+ (Block 1 = OP01-OP04 rotated out April 2026)
// ST sets: ST01-ST12 are Block 1 (out), ST13+ are Standard
// EB01 = Block 1 (out), EB02+ = Standard
const STANDARD_SETS = [
  'OP05','OP06','OP07','OP08','OP09','OP10','OP11','OP12','OP13','OP14','OP15',
  'EB02','EB03','EB04',
  'ST13','ST14','ST15','ST16','ST17','ST18','ST19','ST20',
  'ST21','ST22','ST23','ST24','ST25','ST26','ST27','ST28',
  'PRB01','PRB02',
]

function isStandard(card) {
  return STANDARD_SETS.includes(card.set)
}

const COLORS = ['Red','Green','Blue','Purple','Yellow','Black']

function cardMatchesColor(card, color) {
  if (!card.color) return false
  // Multi-color cards have slash-separated colors e.g. "Red/Green"
  return card.color.split('/').map(c => c.trim()).includes(color)
}

export default function HomeScreen({ decks, cards, faq = {}, onStart }) {
  const [mode, setMode]               = useState(null)
  const [selectedDeck, setSelectedDeck] = useState(null)
  const [filterColor, setFilterColor] = useState('All')
  const [filterFormat, setFilterFormat] = useState('All') // 'All' | 'Standard' | 'Extended' | 'Meta'
  const [query, setQuery]             = useState('')

  // Search by card code (P-001, OP16-080) or name. Code match is prioritised.
  const matches = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (q.length < 2) return []
    const byId = [], byName = []
    for (const c of cards) {
      const id = c.id.toLowerCase()
      if (id.includes(q)) byId.push(c)
      else if ((c.name || '').toLowerCase().includes(q)) byName.push(c)
    }
    return [...byId, ...byName].slice(0, 8)
  }, [query, cards])

  // "Meta Cards" = the unique pool of every card that appears across all meta
  // decks (leaders included), so you can drill it by color (e.g. all yellow
  // cards seen in the meta).
  const metaCardIds = useMemo(() => {
    const ids = new Set()
    decks.forEach(d => {
      if (d.leader) ids.add(d.leader)
      ;(d.cards || []).forEach(id => ids.add(id))
    })
    return ids
  }, [decks])

  function getPool() {
    let pool = cards
    if (filterFormat === 'Standard') pool = pool.filter(isStandard)
    if (filterFormat === 'Meta')     pool = pool.filter(c => metaCardIds.has(c.id))
    if (filterColor !== 'All') pool = pool.filter(c => cardMatchesColor(c, filterColor))
    return pool
  }

  const pool = getPool()

  function handleStart() {
    if (mode === 'random') {
      onStart({ mode: 'random', cards: pool })
    } else if (mode === 'deck' && selectedDeck) {
      onStart({ mode: 'deck', deck: selectedDeck })
    }
  }

  const canStart = mode === 'random'
    ? pool.length > 0
    : (mode === 'deck' && selectedDeck != null)

  return (
    <div className="home">
      <header className="home__header">
        <div className="home__emblem">⚓</div>
        <h1 className="home__title">Judge Trainer</h1>
        <p className="home__subtitle">One Piece Card Game</p>
      </header>

      <section className="home__search">
        <input
          type="text"
          className="home__search-input"
          placeholder="Search a card by code or name (e.g. OP16-080, Luffy)"
          value={query}
          onChange={e => setQuery(e.target.value)}
          autoComplete="off"
        />
        {matches.length > 0 && (
          <ul className="home__search-results">
            {matches.map(c => (
              <li key={c.id}>
                <button className="search-result" onClick={() => onStart({ mode: 'lookup', card: c })}>
                  <span className="search-result__id">{c.id}</span>
                  <span className="search-result__name">{c.name}</span>
                  {(faq[c.id]?.length > 0) && (
                    <span className="search-result__faq">FAQ {faq[c.id].length}</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
        {query.trim().length >= 2 && matches.length === 0 && (
          <p className="home__search-empty">No card matches “{query.trim()}”.</p>
        )}
      </section>

      <section className="home__modes">
        <h2 className="home__section-label">Choose Mode</h2>
        <div className="home__mode-cards">
          <button
            className={`mode-card ${mode === 'random' ? 'mode-card--active' : ''}`}
            onClick={() => { setMode('random'); setSelectedDeck(null) }}
          >
            <span className="mode-card__icon">🎲</span>
            <span className="mode-card__name">Random</span>
            <span className="mode-card__desc">All cards from the catalog, shuffled randomly</span>
          </button>
          <button
            className={`mode-card ${mode === 'deck' ? 'mode-card--active' : ''}`}
            onClick={() => setMode('deck')}
          >
            <span className="mode-card__icon">🗂️</span>
            <span className="mode-card__name">Meta Deck</span>
            <span className="mode-card__desc">Study a specific meta deck card pool</span>
          </button>
        </div>
      </section>

      {mode === 'random' && (
        <section className="home__options">

          {/* Format filter */}
          <h2 className="home__section-label">Format</h2>
          <div className="home__format-filters">
            {['All','Standard','Extended','Meta'].map(f => (
              <button
                key={f}
                className={`format-pill ${filterFormat === f ? 'format-pill--active' : ''}`}
                onClick={() => setFilterFormat(f)}
              >
                {f === 'Meta' ? 'Meta Cards' : f}
                {f === 'Standard' && <span className="format-pill__sub">OP05+</span>}
                {f === 'Extended' && <span className="format-pill__sub">All sets</span>}
                {f === 'All' && <span className="format-pill__sub">No filter</span>}
                {f === 'Meta' && <span className="format-pill__sub">From meta decks</span>}
              </button>
            ))}
          </div>

          {/* Color filter */}
          <h2 className="home__section-label" style={{ marginTop: '1rem' }}>Color</h2>
          <div className="home__color-filters">
            <button
              className={`color-pill ${filterColor === 'All' ? 'color-pill--active' : ''}`}
              onClick={() => setFilterColor('All')}
            >
              All
            </button>
            {COLORS.map(c => (
              <button
                key={c}
                className={`color-pill color-pill--${c.toLowerCase()} ${filterColor === c ? 'color-pill--active' : ''}`}
                onClick={() => setFilterColor(c)}
              >
                {c}
              </button>
            ))}
          </div>

          <p className="home__count">
            {pool.length} card{pool.length !== 1 ? 's' : ''} in pool
            {filterColor !== 'All' && ' (includes multi-color)'}
          </p>

          {pool.length === 0 && (
            <p className="home__count" style={{ color: 'var(--red-bright)', marginTop: '0.3rem' }}>
              No cards match this filter combination.
            </p>
          )}
        </section>
      )}

      {mode === 'deck' && (
        <section className="home__options">
          <h2 className="home__section-label">Select Deck</h2>
          {decks.length === 0 ? (
            <p className="home__count">No meta decks available yet.</p>
          ) : (
            <div className="home__deck-list">
              {decks.map(deck => (
                <button
                  key={deck.id}
                  className={`deck-item ${selectedDeck?.id === deck.id ? 'deck-item--active' : ''}`}
                  onClick={() => setSelectedDeck(deck)}
                >
                  <span className="deck-item__name">{deck.name}</span>
                  <span className="deck-item__meta">{deck.cards.length} cards · {deck.set}</span>
                  {deck.description && (
                    <span className="deck-item__desc">{deck.description}</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </section>
      )}

      <div className="home__cta">
        <button
          className="btn-start"
          disabled={!canStart}
          onClick={handleStart}
        >
          Start Session
        </button>
      </div>

      <footer className="home__footer">
        <p className="home__footer-credit">
          Made by <a
            href="https://github.com/LukeTheCut-prog"
            target="_blank"
            rel="noopener noreferrer"
            className="home__footer-link"
          >LukeTheCut</a>
        </p>
        <p>Card data via optcgapi.com & Limitless TCG · Not affiliated with Bandai</p>
      </footer>
    </div>
  )
}
