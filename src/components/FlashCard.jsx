import { useState } from 'react'
import { getColorVar, formatPower, formatCost, formatCounter } from '../utils/helpers.js'
import './FlashCard.css'

function FaqItem({ entry, index }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="fc-faq__item">
      <div className="fc-faq__q">
        <span className="fc-faq__tag">Q{index + 1}</span>
        <span className="fc-faq__text">{entry.q}</span>
      </div>
      {open ? (
        <div className="fc-faq__a">
          <span className="fc-faq__tag fc-faq__tag--a">A</span>
          <span className="fc-faq__text">{entry.a}</span>
        </div>
      ) : (
        <button className="fc-faq__toggle" onClick={() => setOpen(true)}>
          Show answer
        </button>
      )}
    </div>
  )
}

export default function FlashCard({ card, faqEntries = [], onNext, onHome, current, total }) {
  const [revealed, setRevealed] = useState(false)
  const [imgError, setImgError]  = useState(false)

  const colorVar = getColorVar(card.color)

  function handleReveal() {
    setRevealed(true)
  }

  function handleNext() {
    setRevealed(false)
    setImgError(false)
    onNext()
  }

  return (
    <div
      className={`flashcard-wrapper${!revealed ? ' flashcard-wrapper--tappable' : ''}`}
      style={{ '--card-color': `var(${colorVar})` }}
    >

      {/* Progress bar */}
      <div className="fc-progress">
        <div className="fc-progress__bar" style={{ width: `${(current / total) * 100}%` }} />
        <span className="fc-progress__label">{current} / {total}</span>
      </div>

      {/* Top bar: card ID + home button */}
      <div className="fc-topbar">
        <div className="fc-id">
          <span className="fc-id__code">{card.id}</span>
          <span className="fc-id__type">{card.type}</span>
        </div>
        <button className="fc-home-btn" onClick={onHome} title="Back to Home">
          ⚓ Home
        </button>
      </div>

      {/* Card image — artwork always visible, bottom text area blurred until revealed */}
      <div className="fc-image-wrap">
        {!imgError ? (
          <div className="fc-card-container">
            {/* Full card underneath — visible when revealed */}
            <img
              src={card.image_url}
              alt={card.name}
              className="fc-image"
              onError={() => setImgError(true)}
            />
            {/* Blurred overlay on the bottom ~35% (text area) */}
            {!revealed && (
              <div className="fc-blur-overlay" onClick={handleReveal}>
                <div className="fc-blur-mask" />
                <span className="fc-blur-hint">tap to reveal effect</span>
              </div>
            )}
          </div>
        ) : (
          <div className="fc-image-fallback">
            <span className="fc-image-fallback__id">{card.id}</span>
            <span className="fc-image-fallback__name">{card.name}</span>
          </div>
        )}
      </div>

      {/* Stats row — always visible */}
      <div className="fc-stats">
        <div className="fc-stat">
          <span className="fc-stat__label">Cost</span>
          <span className="fc-stat__value">{formatCost(card.cost)}</span>
        </div>
        <div className="fc-stat fc-stat--power">
          <span className="fc-stat__label">Power</span>
          <span className="fc-stat__value">{formatPower(card.power)}</span>
        </div>
        <div className="fc-stat">
          <span className="fc-stat__label">Counter</span>
          <span className="fc-stat__value">{formatCounter(card.counter)}</span>
        </div>
      </div>

      {/* Reveal section — shown after tap */}
      {revealed && (
        <div className="fc-reveal-area">
          <div className="fc-effect" style={{ animation: 'flip-in 0.3s ease both' }}>
            <div className="fc-effect__name">{card.name}</div>
            <div className="fc-effect__meta">
              <span className="fc-badge fc-badge--color" style={{ '--b-color': `var(${colorVar})` }}>{card.color}</span>
              {card.attribute && <span className="fc-badge">{card.attribute}</span>}
            </div>
            <p className="fc-effect__text">{card.effect}</p>
          </div>

          {faqEntries.length > 0 && (
            <div className="fc-faq">
              <div className="fc-faq__title">
                Official FAQ · {faqEntries.length}
              </div>
              {faqEntries.map((entry, i) => (
                <FaqItem key={i} entry={entry} index={i} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Navigation */}
      <div className="fc-nav">
        {revealed && (
          <button className="fc-next-btn" onClick={handleNext}>
            {current < total ? 'Next Card →' : 'Finish Session'}
          </button>
        )}
      </div>
    </div>
  )
}
