/**
 * Error Boundary Component
 * Catches JavaScript errors in child component tree and displays fallback UI
 */

import React from 'react'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    // Update state so next render shows fallback UI
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    // Log error details
    this.setState({ errorInfo })
    
    // Send to error tracking service in production
    if (process.env.NODE_ENV === 'production') {
      // Example: Sentry.captureException(error, { extra: errorInfo })
      console.error('Production error logged:', error, errorInfo)
    }
    
    // Log to console in development
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  handleReload = () => {
    window.location.reload()
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
    if (this.props.onReset) {
      this.props.onReset()
    }
  }

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      return this.props.fallback || (
        <div style={styles.container}>
          <div style={styles.card}>
            <h2 style={styles.title}>😔 出现了一些问题</h2>
            <p style={styles.message}>
              应用程序遇到了错误。我们已经记录了这个问题。
            </p>
            
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <div style={styles.errorDetails}>
                <details style={{ whiteSpace: 'pre-wrap' }}>
                  <summary style={styles.summary}>查看错误详情 (仅开发模式)</summary>
                  <p style={styles.errorText}>{this.state.error.toString()}</p>
                  <p style={styles.stackText}>{this.state.errorInfo?.componentStack}</p>
                </details>
              </div>
            )}
            
            <div style={styles.buttonGroup}>
              <button onClick={this.handleReset} style={styles.primaryButton}>
                尝试恢复
              </button>
              <button onClick={this.handleReload} style={styles.secondaryButton}>
                重新加载页面
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

// Styles
const styles = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    padding: '20px',
    backgroundColor: '#f5f5f5',
  },
  card: {
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '32px',
    maxWidth: '600px',
    width: '100%',
    boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
    textAlign: 'center',
  },
  title: {
    margin: '0 0 16px 0',
    color: '#333',
    fontSize: '24px',
  },
  message: {
    color: '#666',
    marginBottom: '24px',
    lineHeight: '1.5',
  },
  errorDetails: {
    marginBottom: '24px',
    textAlign: 'left',
    backgroundColor: '#f8f8f8',
    padding: '16px',
    borderRadius: '8px',
    fontSize: '14px',
  },
  summary: {
    cursor: 'pointer',
    color: '#666',
    fontWeight: 'bold',
    marginBottom: '8px',
  },
  errorText: {
    color: '#d32f2f',
    fontFamily: 'monospace',
    marginBottom: '8px',
  },
  stackText: {
    color: '#666',
    fontFamily: 'monospace',
    fontSize: '12px',
  },
  buttonGroup: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'center',
  },
  primaryButton: {
    padding: '12px 24px',
    backgroundColor: '#1976d2',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '16px',
    fontWeight: '500',
  },
  secondaryButton: {
    padding: '12px 24px',
    backgroundColor: 'transparent',
    color: '#1976d2',
    border: '1px solid #1976d2',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '16px',
    fontWeight: '500',
  },
}

// Async Error Boundary for async rendering
export function AsyncErrorBoundary({ children, fallback }) {
  const [hasError, setHasError] = React.useState(false)
  
  React.useEffect(() => {
    const handleError = (error) => {
      console.error('Async error:', error)
      setHasError(true)
    }
    
    window.addEventListener('error', handleError)
    window.addEventListener('unhandledrejection', handleError)
    
    return () => {
      window.removeEventListener('error', handleError)
      window.removeEventListener('unhandledrejection', handleError)
    }
  }, [])
  
  if (hasError) {
    return fallback || <ErrorBoundary fallback /> 
  }
  
  return children
}

export default ErrorBoundary
