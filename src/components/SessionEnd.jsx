import './SessionEnd.css'

export default function SessionEnd({ total, deckName, onRestart, onHome }) {
  return (
    <div className="session-end">
      <div className="session-end__icon">🏴‍☠️</div>
      <h2 className="session-end__title">Session Complete</h2>
      <p className="session-end__sub">
        You reviewed <strong>{total}</strong> card{total !== 1 ? 's' : ''}
        {deckName ? ` from ${deckName}` : ''}.
      </p>
      <div className="session-end__actions">
        <button className="btn-restart" onClick={onRestart}>
          🔁 Study Again
        </button>
        <button className="btn-home" onClick={onHome}>
          ⚓ Back to Home
        </button>
      </div>
    </div>
  )
}
