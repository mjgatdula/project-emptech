import { LuLoaderCircle } from 'react-icons/lu'

export default function Loading({ label = 'Loading...', inline = false }) {
  const Container = inline ? 'span' : 'div'

  return (
    <Container
      role="status"
      aria-live="polite"
      aria-busy="true"
      className={`app-loading ${inline ? 'inline-flex text-inherit' : 'flex w-full justify-center py-12 text-slate-600'} items-center gap-3 text-sm font-medium`}
    >
      <LuLoaderCircle
        aria-hidden="true"
        focusable="false"
        className="h-5 w-5 shrink-0 animate-spin motion-reduce:animate-none"
      />
      <span>{label}</span>
    </Container>
  )
}
