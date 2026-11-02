const labels = { pending: 'Pending review', approved: 'Approved', rejected: 'Not approved', verified: 'Ownership verified', released: 'Returned to owner', in_custody: 'In staff custody', closed: 'Closed', expired: 'Expired', withdrawn: 'Withdrawn' }
export default function StatusBadge({ value = 'pending' }) {
  const tone = ['approved', 'verified', 'released'].includes(value) ? 'positive' : value === 'rejected' ? 'negative' : ['closed', 'expired', 'withdrawn'].includes(value) ? 'neutral' : 'pending'
  return <span className={`status-badge status-${tone}`}><span aria-hidden="true" />{labels[value] || value.replaceAll('_', ' ')}</span>
}
