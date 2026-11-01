import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Sample from './sample/Sample'

createRoot(document.getElementById('root')!).render(<StrictMode><Sample /></StrictMode>)
