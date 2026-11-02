import { LuImage } from 'react-icons/lu'

// Shared empty-photo placeholder. Selected uploads have their own real preview.
export default function ItemIcon({ className = 'h-6 w-6' }) {
  return <LuImage aria-hidden="true" focusable="false" className={className} />
}
