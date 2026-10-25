import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'

export function CarArt({ large = false }: { large?: boolean }) {
  return <svg className={large ? 'car-art large' : 'car-art'} viewBox="0 0 440 180" fill="none" aria-hidden="true">
    <ellipse cx="224" cy="151" rx="174" ry="9" fill="currentColor" opacity=".08" />
    <path d="M48 120 64 92 120 80 166 40H273L324 81 376 95 394 120V139H48Z" fill="currentColor" opacity=".14" />
    <path d="m66 93 57-10 44-40h104l52 40 53 15 15 23v17H50v-17l16-28Z" stroke="currentColor" strokeWidth="3" strokeLinejoin="round" />
    <path d="m145 81 30-29h40v29Zm82 0V52h38l35 29Z" fill="currentColor" opacity=".35" />
    <path d="M219 88v41m19-33h13M55 112h30m277-4h20" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    {[119, 323].map(x => <g key={x}><circle cx={x} cy="137" r="24" fill="#f5f4ee" stroke="currentColor" strokeWidth="5" /><circle cx={x} cy="137" r="11" fill="currentColor" opacity=".5" /></g>)}
  </svg>
}
export function Notice({ children, error = false }: { children: ReactNode; error?: boolean }) {
  return <div className={error ? 'notice error' : 'notice'} role={error ? 'alert' : 'status'}>{children}</div>
}

export function Modal({ title, children, close, busy = false }: { title: string; children: ReactNode; close: () => void; busy?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => { const dialog = ref.current!; dialog.showModal(); return () => dialog.close() }, [])
  return <dialog ref={ref} className="modal" aria-labelledby="modal-title" onCancel={event => { event.preventDefault(); if (!busy) close() }}><div className="flex items-center justify-between gap-4 mb-6"><h2 id="modal-title">{title}</h2><button className="text-button" aria-label="Close dialog" disabled={busy} onClick={close}>✕</button></div>{children}</dialog>
}
