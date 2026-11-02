import { useState } from 'react'
import { LuEye, LuEyeOff } from 'react-icons/lu'

export default function PasswordField({ id, name, label, autoComplete, minLength, invalid = false, describedBy }) {
  const [visible, setVisible] = useState(false)

  return (
    <div>
      <label htmlFor={id} className="block text-sm font-semibold text-slate-700">{label} *</label>
      <div className="relative mt-2">
        <input
          id={id}
          name={name}
          type={visible ? 'text' : 'password'}
          autoComplete={autoComplete}
          required
          minLength={minLength}
          aria-invalid={invalid || undefined}
          aria-describedby={describedBy}
          className={`field !mt-0 !pr-12 ${invalid ? 'border-red-600' : 'border-slate-300 focus:border-brand-500'}`}
        />
        <button
          type="button"
          aria-label={`${visible ? 'Hide' : 'Show'} ${label.toLowerCase()}`}
          aria-pressed={visible}
          aria-controls={id}
          onClick={() => setVisible(!visible)}
          className="absolute inset-y-0 right-0 grid w-11 place-items-center rounded-r-xl text-slate-600 hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-brand-500"
        >
          {visible ? <LuEyeOff aria-hidden="true" focusable="false" className="h-5 w-5" /> : <LuEye aria-hidden="true" focusable="false" className="h-5 w-5" />}
        </button>
      </div>
    </div>
  )
}
