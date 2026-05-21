import { useState, useEffect } from 'react'
import { getToken, getCachedUser, clearToken } from './auth'

const cardStyle = {
  background: 'rgba(28,28,30,0.92)',
  border: '0.5px solid rgba(255,255,255,0.08)',
  backdropFilter: 'blur(20px) saturate(180%)',
  WebkitBackdropFilter: 'blur(20px) saturate(180%)',
  borderRadius: '20px',
  padding: '24px',
  marginBottom: '16px',
}

const rowStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '14px 0',
  borderBottom: '0.5px solid rgba(255,255,255,0.06)',
}

function Toggle({ checked, onChange }) {
  return (
    <div
      onClick={() => onChange(!checked)}
      style={{
        width: '48px', height: '28px', borderRadius: '14px',
        background: checked ? '#3b82f6' : 'rgba(120,120,128,0.3)',
        cursor: 'pointer', position: 'relative',
        transition: 'background 0.2s',
      }}
    >
      <div style={{
        width: '22px', height: '22px', borderRadius: '50%',
        background: '#fff', position: 'absolute', top: '3px',
        left: checked ? '23px' : '3px',
        transition: 'left 0.2s', boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
      }} />
    </div>
  )
}

function SettingRow({ label, description, children }) {
  return (
    <div style={rowStyle}>
      <div>
        <div style={{ fontSize: '15px', color: '#fff' }}>{label}</div>
        {description && <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)', marginTop: '2px' }}>{description}</div>}
      </div>
      {children}
    </div>
  )
}

const SETTINGS_KEY = 'emotion-sphere-settings'

function getSettings() {
  try {
    return JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}')
  } catch { return {} }
}

function saveSettings(s) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s))
}

export default function SettingsPage() {
  const token = getToken()
  const user = getCachedUser()
  const [settings, setSettings] = useState(getSettings)
  const [showConfirm, setShowConfirm] = useState(false)

  const update = (key, value) => {
    const next = { ...settings, [key]: value }
    setSettings(next)
    saveSettings(next)
  }

  const handleClearCache = () => {
    localStorage.removeItem('emotion-sphere-history')
    localStorage.removeItem('emotion-sphere-stats')
    setShowConfirm(false)
    alert('本地缓存已清除')
  }

  const handleExportData = () => {
    const data = {
      settings: getSettings(),
      user: getCachedUser(),
      exportedAt: new Date().toISOString(),
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `emotion-sphere-export-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (!token) {
    return (
      <div style={{ padding: '40px 20px', textAlign: 'center', color: '#fff' }}>
        <h2>请先登录</h2>
        <button
          onClick={() => window.location.href = '/login'}
          style={{
            padding: '12px 24px', borderRadius: '12px', border: 'none',
            background: '#3b82f6', color: '#fff', fontSize: '15px', cursor: 'pointer', marginTop: '16px'
          }}
        >
          前往登录
        </button>
      </div>
    )
  }

  return (
    <div style={{ padding: '20px', maxWidth: '600px', margin: '0 auto', color: '#fff' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '24px' }}>设置</h1>

      {/* Notification Settings */}
      <div style={cardStyle}>
        <h3 style={{ margin: '0 0 8px', fontSize: '16px', fontWeight: 600 }}>通知设置</h3>
        <SettingRow label="习惯提醒" description="在习惯执行时间发送提醒">
          <Toggle checked={settings.habitReminder !== false} onChange={v => update('habitReminder', v)} />
        </SettingRow>
        <SettingRow label="心理洞察" description="当系统发现重要心理模式时通知">
          <Toggle checked={settings.psychInsight !== false} onChange={v => update('psychInsight', v)} />
        </SettingRow>
        <SettingRow label="每日总结" description="每天晚上推送当日情绪和行为总结">
          <Toggle checked={settings.dailySummary ?? true} onChange={v => update('dailySummary', v)} />
        </SettingRow>
      </div>

      {/* Display Settings */}
      <div style={cardStyle}>
        <h3 style={{ margin: '0 0 8px', fontSize: '16px', fontWeight: 600 }}>显示设置</h3>
        <SettingRow label="3D 情绪星球" description="在首页显示 3D 情绪可视化">
          <Toggle checked={settings.show3D !== false} onChange={v => update('show3D', v)} />
        </SettingRow>
        <SettingRow label="动画效果" description="界面过渡动画">
          <Toggle checked={settings.animations !== false} onChange={v => update('animations', v)} />
        </SettingRow>
        <SettingRow label="简洁模式" description="减少视觉信息密度">
          <Toggle checked={settings.compactMode ?? false} onChange={v => update('compactMode', v)} />
        </SettingRow>
      </div>

      {/* Privacy Settings */}
      <div style={cardStyle}>
        <h3 style={{ margin: '0 0 8px', fontSize: '16px', fontWeight: 600 }}>隐私与数据</h3>
        <SettingRow label="匿名祈祷" description="默认以匿名方式发布代祷">
          <Toggle checked={settings.anonymousPrayer ?? false} onChange={v => update('anonymousPrayer', v)} />
        </SettingRow>
        <SettingRow label="数据分析" description="允许系统分析行为数据以优化建议">
          <Toggle checked={settings.dataAnalysis !== false} onChange={v => update('dataAnalysis', v)} />
        </SettingRow>
      </div>

      {/* Data Management */}
      <div style={cardStyle}>
        <h3 style={{ margin: '0 0 8px', fontSize: '16px', fontWeight: 600 }}>数据管理</h3>
        <SettingRow label="导出数据" description="导出你的设置和数据为 JSON 文件">
          <button
            onClick={handleExportData}
            style={{
              padding: '8px 16px', borderRadius: '8px', border: 'none',
              background: 'rgba(59,130,246,0.2)', color: '#3b82f6',
              fontSize: '13px', fontWeight: 600, cursor: 'pointer',
            }}
          >
            导出
          </button>
        </SettingRow>
        <SettingRow label="清除缓存" description="清除本地缓存的数据">
          {showConfirm ? (
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={handleClearCache}
                style={{
                  padding: '8px 12px', borderRadius: '8px', border: 'none',
                  background: 'rgba(239,68,68,0.2)', color: '#ef4444',
                  fontSize: '12px', fontWeight: 600, cursor: 'pointer',
                }}
              >
                确认
              </button>
              <button
                onClick={() => setShowConfirm(false)}
                style={{
                  padding: '8px 12px', borderRadius: '8px', border: 'none',
                  background: 'rgba(120,120,128,0.2)', color: '#fff',
                  fontSize: '12px', cursor: 'pointer',
                }}
              >
                取消
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowConfirm(true)}
              style={{
                padding: '8px 16px', borderRadius: '8px', border: 'none',
                background: 'rgba(239,68,68,0.15)', color: '#ef4444',
                fontSize: '13px', fontWeight: 600, cursor: 'pointer',
              }}
            >
              清除
            </button>
          )}
        </SettingRow>
      </div>

      {/* About */}
      <div style={cardStyle}>
        <h3 style={{ margin: '0 0 8px', fontSize: '16px', fontWeight: 600 }}>关于</h3>
        <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.6)', lineHeight: 1.8 }}>
          <p style={{ margin: '4px 0' }}>应用版本: v1.0.0</p>
          <p style={{ margin: '4px 0' }}>用户 ID: {user?.id || '—'}</p>
          <p style={{ margin: '4px 0' }}>情感星球 — 基于心理学的情绪管理与人格成长系统</p>
        </div>
      </div>
    </div>
  )
}
