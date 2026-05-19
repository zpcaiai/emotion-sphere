import { useState, useEffect, useCallback } from 'react'
import { detectExecutionCrash } from './api'
import { getToken } from './auth'

export default function CrashDetectionPanel({ onCrashDetected, onStateChange }) {
  const [checkInProgress, setCheckInProgress] = useState(false)
  const [lastCheck, setLastCheck] = useState(null)
  const [crashState, setCrashState] = useState(null)
  const [telemetry, setTelemetry] = useState({ task_attempts: 0, escape_urges: 0, last_session_minutes: 0 })

  const runDetection = useCallback(async () => {
    setCheckInProgress(true)
    try {
      const token = getToken()
      const result = await detectExecutionCrash(telemetry, token)
      setCrashState(result)
      setLastCheck(new Date())
      if (result.detected && onCrashDetected) onCrashDetected(result)
      if (onStateChange) onStateChange(result)
    } catch (err) {
      console.error('Crash detection failed:', err)
    } finally {
      setCheckInProgress(false)
    }
  }, [telemetry, onCrashDetected, onStateChange])

  useEffect(() => { const i = setInterval(runDetection, 30000); runDetection(); return () => clearInterval(i) }, [runDetection])

  const getRiskColor = (r) => r >= 0.7 ? '#ff4444' : r >= 0.4 ? '#ff8800' : '#44ff44'
  const getRiskLabel = (r) => r >= 0.7 ? '高风险' : r >= 0.4 ? '中等风险' : '低风险'

  return (
    <div className="exec-panel crash-panel">
      <h3 className="panel-title"><span className="panel-icon">⚠️</span>执行力崩溃检测</h3>
      <div className="telemetry-inputs">
        <div className="telemetry-row"><label>今日尝试任务</label><input type="number" min="0" value={telemetry.task_attempts} onChange={(e) => setTelemetry({...telemetry, task_attempts: parseInt(e.target.value) || 0})} /></div>
        <div className="telemetry-row"><label>逃避冲动次数</label><input type="number" min="0" value={telemetry.escape_urges} onChange={(e) => setTelemetry({...telemetry, escape_urges: parseInt(e.target.value) || 0})} /></div>
        <div className="telemetry-row"><label>上次专注(分钟)</label><input type="number" min="0" value={telemetry.last_session_minutes} onChange={(e) => setTelemetry({...telemetry, last_session_minutes: parseInt(e.target.value) || 0})} /></div>
      </div>
      <button className="detect-btn" onClick={runDetection} disabled={checkInProgress}>{checkInProgress ? '检测中...' : '立即检测'}</button>
      {crashState && (
        <div className="crash-result">
          <div className="risk-indicator" style={{ background: getRiskColor(crashState.risk_score) }}>
            <span className="risk-value">{Math.round(crashState.risk_score * 100)}%</span>
            <span className="risk-label">{getRiskLabel(crashState.risk_score)}</span>
          </div>
          {crashState.detected && (
            <div className="crash-alert">
              <div className="alert-header"><span className="alert-icon">🚨</span><span>崩溃预警触发</span></div>
              <div className="alert-details">
                <p><strong>模式:</strong> {crashState.crash_pattern}</p>
                <p><strong>核心阻力:</strong> {crashState.core_resistance}</p>
                {crashState.escalation_needed && <p className="escalation-warning">⚡ 需要升级干预</p>}
              </div>
              <div className="circuit-breaker">
                <h4>熔断保护已激活</h4>
                <ul>{crashState.circuit_breaker_recommendations?.map((rec, i) => <li key={i}>{rec}</li>)}</ul>
              </div>
            </div>
          )}
          {!crashState.detected && crashState.risk_score < 0.4 && <div className="status-ok"><span className="ok-icon">✓</span><span>执行力状态正常</span></div>}
        </div>
      )}
      {lastCheck && <div className="last-check">上次检测: {lastCheck.toLocaleTimeString()}</div>}
    </div>
  )
}
