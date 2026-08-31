// Fisher-Yates shuffle — returns a new array
export function shuffle(arr) {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

// Map card color to CSS variable name
export const COLOR_MAP = {
  Red:    '--red',
  Blue:   '--blue-op',
  Green:  '--green-op',
  Purple: '--purple-op',
  Yellow: '--yellow-op',
  Black:  '--black-op',
}

export function getColorVar(color) {
  return COLOR_MAP[color] ?? '--text-muted'
}

export function formatPower(power) {
  if (power == null) return '—'
  return power.toLocaleString()
}

export function formatCost(cost) {
  if (cost == null) return '—'
  return cost
}

export function formatCounter(counter) {
  if (counter == null) return '—'
  return counter === 0 ? '0' : `+${counter.toLocaleString()}`
}

// Every printing of a card: the base art plus any alternate/parallel arts
// downloaded into `alt_images`. Cards with no alt art just return the one.
export function cardArts(card) {
  return [card.image_url, ...(card.alt_images || [])].filter(Boolean)
}

// Pick one printing at random, so a card can come up as the regular art one
// time and an alternate art the next.
export function randomArt(card) {
  const arts = cardArts(card)
  if (arts.length === 0) return null
  return arts[Math.floor(Math.random() * arts.length)]
}
