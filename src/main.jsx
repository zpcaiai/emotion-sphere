import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { QueryProvider } from './providers/QueryProvider'
import ErrorBoundary from './components/ErrorBoundary'
import { router } from './router'
import { registerServiceWorker } from './pwa'
import './styles.css'

registerServiceWorker()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <QueryProvider>
        <RouterProvider router={router} />
      </QueryProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)
