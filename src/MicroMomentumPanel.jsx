import { useState, useEffect, useCallback } from 'react'
import { fetchMicroMomentum, completeMicroSession } from './api'
import { getToken } from './auth'

export default function MicroMomentumPanel() {
  const [momentum, setMomentum] = useState(null)
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])

  const loadMomentum = useCallback(async () => {
    setLoading(true)
    try {
      const token = getToken()
      const result = await fetchMicroMomentum(token)
      setMomentum(result)
      if (result.session_history) setHistory(result.session_history)
    } catch (err) { console.error('Failed to load momentum:', err) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { loadMomentum() }, [loadMomentum])

  const completeSession = async (sessionId, actualDuration, success) => {
    try {
      const token = getToken()
      await completeMicroSession(sessionId, { actual_duration_minutes: actualDuration, completed: success }, '', token)
      loadMomentum()
    } catch (err) { console.error('Failed to complete session:', err) }
  }

  const getLevelColor = (level) => ({ '1': '#95a5a6', '2': '#3498db', '3': '#2ecc71', '4': '#f39c12', '5': '#e74c3c' }[level] || '#95a5a6')

  if (!momentum && !loading) return <div className="exec-panel momentum-panel"><h3 className="panel-title"><span className="panel-icon">📈</span>微动量</h3><p>加载中...</p></div>

  return (
    <div className="exec-panel momentum-panel">
      <h3 className="panel-title"><span className="panel-icon">📈</span>微动量追踪</h3>
      {momentum && (
        <>
          <div className="momentum-score-card">
            <div className="score-circle" style={{ borderColor: getLevelColor(momentum.momentum_level) }}>
              <span className="score-value">{momentum.momentum_score}</span>
              <span className="score-max">/100</span>
            </div>
            <div className="level-badge" style={{ background: getLevelColor(momentum.momentum_level) }}>Level {momentum.momentum_level}</div>
          </div>
          <div className="momentum-stats">
            <div className="stat-item"><label>今日完成</label><span>{momentum.sessions_completed_today || 0}</span></div>
            <div className="stat-item"><label>连续天数</label><span>{momentum.streak_days || 0}</span></div>
            <div className="stat-item"><label>总分钟</label><span>{momentum.total_focus_minutes || 0}</span></div>
          </div>
          <div className="velocity-indicator">
            <label>动量速度</label>
            <div className="velocity-bar">
              <div className="velocity-fill" style={{ width: `${Math.min(Math.abs(momentum.velocity || 0) * 10, 100)}%`, background: (momentum.velocity || 0) >= 0 ? '#2ecc71' : '#e74c3c' }} />
            </div>
            <span className="velocity-value">{momentum.velocity > 0 ? '+' : ''}{momentum.velocity}/session</span>
          </div>
        </>
      )}
      {history.length > 0 && (
        <div className="session-history">
          <h4>最近会话</h4>
          {history.slice(0, 5).map((session, idx) => (
            <div key={idx} className="history-item">
              <span className="session-time">{new Date(session.started_at).toLocaleTimeString()}</span>
              <span className="session-duration">{session.actual_duration_minutes || session.planned_duration_minutes}分钟</span>
              <span className={`session-status ${session.completed ? 'success' : 'fail'}`}>{session.completed ? '✓' : '✗'}</span>
            </div>
          ))}
        </div>
      )}
      <button className="refresh-btn" onClick={loadMomentum} disabled={loading}>{loading ? '刷新中...' : '刷新数据'}</button>
    </div>
  )
}
