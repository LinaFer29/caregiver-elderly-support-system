import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './context/AuthProvider.tsx'
import { SelectedElderlyProvider } from './context/SelectedElderlyProvider.tsx'

createRoot(document.getElementById('root')!).render(

  <SelectedElderlyProvider>
    <AuthProvider>
      <StrictMode>
        <App />
      </StrictMode>
    </AuthProvider>
  </SelectedElderlyProvider>
)
