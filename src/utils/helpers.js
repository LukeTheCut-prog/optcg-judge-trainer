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
