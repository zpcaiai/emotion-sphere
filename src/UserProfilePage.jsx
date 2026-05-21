import { useState, useEffect, useCallback } from 'react'
import { getToken, getCachedUser, fetchCurrentUser, logout, setCachedUser } from './auth'
import { updateUserProfile, fetchPersonaProfile, fetchHabitsDashboard, fetchPsychologyDashboard } from './api'

const cardStyle = {
  background: 'rgba(28,28,30,0.92)',
  border: '0.5px solid rgba(255,255,255,0.08)',
  backdropFilter: 'blur(20px) saturate(180%)',
  WebkitBackdropFilter: 'blur(20px) saturate(180%)',
  borderRadius: '20px',
  padding: '24px',
  marginBottom: '16px',
}

const inputStyle = {
  width: '100%',
  minHeight: '44px',
  background: 'rgba(120,120,128,0.18)',
  border: '0.5px solid rgba(255,255,255,0.1)',
  borderRadius: '12px',
  color: '#fff',
  fontSize: '15px',
  padding: '10px 14px',
  boxSizing: 'border-box',
  outline: 'none',
  fontFamily: 'inherit',
}

const btnStyle = {
  padding: '12px 24px',
  borderRadius: '12px',
  border: 'none',
  fontSize: '15px',
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'all 0.2s',
}

function StatCard({ label, value, color = '#3b82f6' }) {
  return (
    <div style={{ textAlign: 'center', flex: 1, minWidth: '80px' }}>
      <div style={{ fontSize: '24px', fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginTop: '4px' }}>{label}</div>
    </div>
  )
}

export default function UserProfilePage() {
  const [user, setUser] = useState(getCachedUser())
  const [editing, setEditing] = useState(false)
  const [nickname, setNickname] = useState('')
  const [avatar, setAvatar] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [persona, setPersona] = useState(null)
  const [habits, setHabits] = useState(null)
  const [psychology, setPsychology] = useState(null)

  const token = getToken()

  const loadData = useCallback(async () => {
    if (!token) return
    const u = await fetchCurrentUser()
    if (u) {
      setUser(u)
      setNickname(u.nickname || '')
      setAvatar(u.avatar || '')
    }

    try {
      const p = await fetchPersonaProfile(token)
      setPersona(p)
    } catch {}

    try {
      const h = await fetchHabitsDashboard(token)
      setHabits(h)
    } catch {}

    try {
      const ps = await fetchPsychologyDashboard(token)
      setPsychology(ps)
    } catch {}
  }, [token])

  useEffect(() => { loadData() }, [loadData])

  const handleSave = async () => {
    setSaving(true)
    setMessage('')
    try {
      const result = await updateUserProfile({ nickname, avatar }, token)
      if (result.ok) {
        setUser({ ...user, nickname: result.nickname, avatar: result.avatar })
        setCachedUser({ ...user, nickname: result.nickname, avatar: result.avatar })
        setEditing(false)
        setMessage('保存成功')
      } else {
        setMessage('保存失败')
      }
    } catch (e) {
      setMessage('网络错误: ' + e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleLogout = async () => {
    await logout()
    window.location.href = '/login'
  }

  if (!token) {
    return (
      <div style={{ padding: '40px 20px', textAlign: 'center', color: '#fff' }}>
        <h2>请先登录</h2>
        <button
          onClick={() => window.location.href = '/login'}
          style={{ ...btnStyle, background: '#3b82f6', color: '#fff', marginTop: '16px' }}
        >
          前往登录
        </button>
      </div>
    )
  }

  return (
    <div style={{ padding: '20px', maxWidth: '600px', margin: '0 auto', color: '#fff' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '24px' }}>个人中心</h1>

      {/* Avatar & Basic Info */}
      <div style={{ ...cardStyle, textAlign: 'center' }}>
        <div style={{
          width: '80px', height: '80px', borderRadius: '50%',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          margin: '0 auto 16px', overflow: 'hidden',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '32px'
        }}>
          {user?.avatar
            ? <img src={user.avatar} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            : (user?.nickname?.[0] || '👤')
          }
        </div>
        <h2 style={{ fontSize: '20px', margin: '0 0 4px' }}>{user?.nickname || '未设置昵称'}</h2>
        <p style={{ fontSize: '14px', color: 'rgba(255,255,255,0.5)', margin: 0 }}>{user?.email || ''}</p>
        <p style={{ fontSize: '12px', color: 'rgba(255,255,255,0.3)', marginTop: '8px' }}>
          加入时间: {user?.created_at ? new Date(user.created_at * 1000).toLocaleDateString('zh-CN') : '—'}
        </p>
      </div>

      {/* Edit Profile */}
      <div style={cardStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ margin: 0, fontSize: '16px' }}>编辑资料</h3>
          {!editing && (
            <button
              onClick={() => setEditing(true)}
              style={{ ...btnStyle, padding: '8px 16px', background: 'rgba(59,130,246,0.2)', color: '#3b82f6', fontSize: '13px' }}
            >
              编辑
            </button>
          )}
        </div>
        {editing ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div>
              <label style={{ fontSize: '13px', color: 'rgba(255,255,255,0.6)', marginBottom: '4px', display: 'block' }}>昵称</label>
              <input
                style={inputStyle}
                value={nickname}
                onChange={e => setNickname(e.target.value)}
                placeholder="输入昵称"
                maxLength={64}
              />
            </div>
            <div>
              <label style={{ fontSize: '13px', color: 'rgba(255,255,255,0.6)', marginBottom: '4px', display: 'block' }}>头像 URL</label>
              <input
                style={inputStyle}
                value={avatar}
                onChange={e => setAvatar(e.target.value)}
                placeholder="https://..."
                maxLength={500}
              />
            </div>
            <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
              <button
                onClick={handleSave}
                disabled={saving}
                style={{ ...btnStyle, flex: 1, background: '#3b82f6', color: '#fff', opacity: saving ? 0.6 : 1 }}
              >
                {saving ? '保存中...' : '保存'}
              </button>
              <button
                onClick={() => { setEditing(false); setNickname(user?.nickname || ''); setAvatar(user?.avatar || '') }}
                style={{ ...btnStyle, flex: 1, background: 'rgba(120,120,128,0.2)', color: '#fff' }}
              >
                取消
              </button>
            </div>
            {message && <p style={{ fontSize: '13px', color: message.includes('成功') ? '#22c55e' : '#ef4444', textAlign: 'center' }}>{message}</p>}
          </div>
        ) : (
          <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.7)' }}>
            <p>昵称: {user?.nickname || '—'}</p>
            <p>登录方式: {user?.login_type === 'wxapp' ? '微信' : '邮箱'}</p>
          </div>
        )}
      </div>

      {/* Stats Overview */}
      <div style={cardStyle}>
        <h3 style={{ margin: '0 0 16px', fontSize: '16px' }}>数据概览</h3>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <StatCard label="习惯坚持" value={habits?.total_active_habits || 0} color="#22c55e" />
          <StatCard label="完成率" value={`${habits?.avg_completion_rate || 0}%`} color="#f59e0b" />
          <StatCard label="人格标签" value={persona?.total_tags || 0} color="#8b5cf6" />
          <StatCard label="稳定分" value={persona?.stability_score?.toFixed(1) || '—'} color="#06b6d4" />
        </div>
      </div>

      {/* Persona Summary */}
      {persona && persona.tag_cloud && Object.keys(persona.tag_cloud).length > 0 && (
        <div style={cardStyle}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px' }}>人格画像</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {Object.entries(persona.tag_cloud).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([tag, weight]) => (
              <span key={tag} style={{
                padding: '6px 12px', borderRadius: '16px',
                background: `rgba(139,92,246,${Math.min(weight / 10, 0.4)})`,
                color: '#c4b5fd', fontSize: '13px', fontWeight: 500,
                border: '1px solid rgba(139,92,246,0.3)'
              }}>
                {tag} ({weight.toFixed(1)})
              </span>
            ))}
          </div>
          <div style={{ marginTop: '12px', fontSize: '13px', color: 'rgba(255,255,255,0.5)' }}>
            成长趋势: <span style={{ color: persona.growth_trend === 'improving' ? '#22c55e' : persona.growth_trend === 'declining' ? '#ef4444' : '#f59e0b' }}>
              {persona.growth_trend === 'improving' ? '↑ 上升' : persona.growth_trend === 'declining' ? '↓ 下降' : '→ 稳定'}
            </span>
          </div>
        </div>
      )}

      {/* Logout */}
      <div style={{ marginTop: '32px', textAlign: 'center' }}>
        <button
          onClick={handleLogout}
          style={{ ...btnStyle, background: 'rgba(239,68,68,0.15)', color: '#ef4444', width: '100%' }}
        >
          退出登录
        </button>
      </div>
    </div>
  )
}
