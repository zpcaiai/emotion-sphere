const configuredApiBase = import.meta.env.VITE_API_BASE?.trim()

function resolveDefaultApiBase() {
  if (typeof window === 'undefined') {
    return '/api'
  }

  const hostname = window.location.hostname
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return '/api'  // 本地开发使用 Vite proxy
  }

  // Hugging Space / Netlify / Render：后端和前端同域名，使用相对路径
  if (hostname.includes('hf.space') || hostname.includes('netlify.app') || hostname.includes('onrender.com')) {
    return '/api'
  }

  return '/api'
}

export const API_BASE = configuredApiBase || resolveDefaultApiBase()

export async function fetchLayout() {
  console.log('[api] fetchLayout')
  try {
    const response = await fetch(`${API_BASE}/layout`)
    if (!response.ok) throw new Error('Failed to fetch layout')
    const data = await response.json()
    console.log(`[api] fetchLayout ok: ${data.count} items`)
    return data
  } catch (err) {
    console.log('[api] fetchLayout api failed, fallback to static json', err.message)
    const response = await fetch('/emotion_sphere_layout.json')
    if (!response.ok) throw new Error('Failed to fetch layout (static fallback)')
    const items = await response.json()
    console.log(`[api] fetchLayout static ok: ${items.length} items`)
    return { items, count: items.length }
  }
}

export async function fetchHistory() {
  console.log('[api] fetchHistory')
  const response = await fetch(`${API_BASE}/history`)
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    console.log('[api] fetchHistory backend unavailable, returning empty')
    return { items: [], total: 0 }
  }
  if (!response.ok) throw new Error('Failed to fetch history')
  const data = await response.json()
  console.log(`[api] fetchHistory ok: ${data.items?.length ?? 0} records`)
  return data
}

export async function fetchStats() {
  console.log('[api] fetchStats')
  const response = await fetch(`${API_BASE}/stats`)
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  if (!response.ok) throw new Error('Failed to fetch stats')
  const data = await response.json()
  console.log('[api] fetchStats ok:', data)
  return data
}

export async function trackStats(visitorId) {
  console.log(`[api] trackStats visitorId=${visitorId}`)
  const response = await fetch(`${API_BASE}/stats/track`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ visitorId }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Failed to track stats')
  console.log('[api] trackStats ok:', data)
  return data
}

export async function fetchFeatureDetail(featureKey) {
  console.log(`[api] fetchFeatureDetail key=${featureKey}`)
  const response = await fetch(`${API_BASE}/feature?key=${encodeURIComponent(featureKey)}`)
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  if (!response.ok) throw new Error('Failed to fetch feature detail')
  const data = await response.json()
  console.log(`[api] fetchFeatureDetail ok key=${featureKey}`)
  return data
}

export async function runQuery(payload) {
  console.log(`[api] runQuery query=${payload.query?.slice(0, 60)} rerank=${payload.enableRerank}`)
  const response = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Query failed')
  console.log(`[api] runQuery ok latency=${data.query_latency_ms}ms features=${data.selected_emotions?.length ?? 0}`)
  return data
}

export async function fetchGuidance(query) {
  console.log(`[api] fetchGuidance query=${query?.slice(0, 60)}`)
  const response = await fetch(`${API_BASE}/guidance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Guidance failed')
  console.log(`[api] fetchGuidance ok emotions=${data.core_emotions}`)
  return data
}

export async function fetchSermon(query) {
  console.log(`[api] fetchSermon query=${query?.slice(0, 60)}`)
  const response = await fetch(`${API_BASE}/sermon`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Sermon failed')
  console.log(`[api] fetchSermon ok title=${data.title}`)
  return data
}

export async function fetchBiblicalExample(query) {
  console.log(`[api] fetchBiblicalExample query=${query?.slice(0, 60)}`)
  const response = await fetch(`${API_BASE}/biblical-example`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Biblical example failed')
  console.log(`[api] fetchBiblicalExample ok person=${data.person} era=${data.era}`)
  return data
}

export async function* sendChat(messages, sessionId, token) {
  console.log(`[api] sendChat session=${sessionId} msgs=${messages.length}`)
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ session_id: sessionId || '', messages }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json') && !contentType.includes('text/event-stream')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    console.error('[api] sendChat error:', err)
    throw new Error(err.detail || err.error || 'Chat failed')
  }
  console.log('[api] sendChat stream started')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let totalChunks = 0
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const raw = line.slice(6).trim()
      if (!raw) continue
      try {
        const obj = JSON.parse(raw)
        if (obj.delta) totalChunks++
        if (obj.done) console.log(`[api] sendChat stream done session=${obj.session_id} chunks=${totalChunks}`)
        yield obj
      } catch { /* ignore malformed */ }
    }
  }
}

export async function fetchPrayers(limit = 40, offset = 0, token = null) {
  console.log(`[api] fetchPrayers limit=${limit} offset=${offset}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/prayers?limit=${limit}&offset=${offset}`, { headers })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  if (!response.ok) throw new Error('Failed to fetch prayers')
  const data = await response.json()
  console.log(`[api] fetchPrayers ok: ${data.items?.length ?? 0}/${data.total} items`)
  return data
}

export async function submitPrayer(content, isAnonymous, token) {
  console.log(`[api] submitPrayer anon=${isAnonymous} len=${content.length}`)
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/prayers`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ content, is_anonymous: isAnonymous }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Submit failed')
  console.log(`[api] submitPrayer ok id=${data.id}`)
  return data
}

export async function amenPrayer(prayerId, token) {
  console.log(`[api] amenPrayer id=${prayerId}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/prayers/${prayerId}/amen`, {
    method: 'POST',
    headers,
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Amen failed')
  console.log(`[api] amenPrayer ok id=${prayerId} count=${data.amen_count}`)
  return data
}

export async function updatePrayer(prayerId, content, token) {
  console.log(`[api] updatePrayer id=${prayerId}`)
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/prayers/${prayerId}`, {
    method: 'PUT',
    headers,
    body: JSON.stringify({ content: content.trim() }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Update failed')
  console.log(`[api] updatePrayer ok id=${prayerId}`)
  return data
}

export async function deletePrayer(prayerId, token) {
  console.log(`[api] deletePrayer id=${prayerId}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/prayers/${prayerId}`, {
    method: 'DELETE',
    headers,
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Delete failed')
  console.log(`[api] deletePrayer ok id=${prayerId}`)
  return data
}

export async function restorePrayer(prayerId, token) {
  console.log(`[api] restorePrayer id=${prayerId}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/prayers/${prayerId}/restore`, {
    method: 'POST',
    headers,
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Restore failed')
  console.log(`[api] restorePrayer ok id=${prayerId}`)
  return data
}

// ── Evangelism Prayers (传福音祷告墙) ─────────────────────────

export async function fetchEvangelismPrayers(limit = 40, offset = 0, token = null) {
  console.log(`[api] fetchEvangelismPrayers limit=${limit} offset=${offset}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/evangelism?limit=${limit}&offset=${offset}`, { headers })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  if (!response.ok) throw new Error('Failed to fetch evangelism prayers')
  const data = await response.json()
  console.log(`[api] fetchEvangelismPrayers ok: ${data.items?.length ?? 0}/${data.total} items`)
  return data
}

export async function submitEvangelismPrayer(content, isAnonymous, token) {
  console.log(`[api] submitEvangelismPrayer anon=${isAnonymous} len=${content.length}`)
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/evangelism`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ content: content.trim(), is_anonymous: isAnonymous }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Submit failed')
  console.log(`[api] submitEvangelismPrayer ok id=${data.id}`)
  return data
}

export async function amenEvangelismPrayer(prayerId, token) {
  console.log(`[api] amenEvangelismPrayer id=${prayerId}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/evangelism/${prayerId}/amen`, {
    method: 'POST',
    headers,
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Amen failed')
  console.log(`[api] amenEvangelismPrayer ok id=${prayerId} count=${data.amen_count}`)
  return data
}

export async function updateEvangelismPrayer(prayerId, content, token) {
  console.log(`[api] updateEvangelismPrayer id=${prayerId}`)
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/evangelism/${prayerId}`, {
    method: 'PUT',
    headers,
    body: JSON.stringify({ content: content.trim() }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Update failed')
  console.log(`[api] updateEvangelismPrayer ok id=${prayerId}`)
  return data
}

export async function deleteEvangelismPrayer(prayerId, token) {
  console.log(`[api] deleteEvangelismPrayer id=${prayerId}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/evangelism/${prayerId}`, {
    method: 'DELETE',
    headers,
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Delete failed')
  console.log(`[api] deleteEvangelismPrayer ok id=${prayerId}`)
  return data
}

export async function restoreEvangelismPrayer(prayerId, token) {
  console.log(`[api] restoreEvangelismPrayer id=${prayerId}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/evangelism/${prayerId}/restore`, {
    method: 'POST',
    headers,
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Restore failed')
  console.log(`[api] restoreEvangelismPrayer ok id=${prayerId}`)
  return data
}

export async function submitCheckin(payload, token) {
  console.log(`[api] submitCheckin emotion=${payload.emotionLabel} anon=${!token}`)
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/user/checkin`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Checkin failed')
  console.log(`[api] submitCheckin ok tags=${data.tags_extracted}`)
  return data
}

export async function fetchJournals(token, limit = 50, offset = 0) {
  console.log(`[api] fetchJournals limit=${limit} offset=${offset}`)
  const response = await fetch(`${API_BASE}/devotion/journals?limit=${limit}&offset=${offset}`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Fetch journals failed')
  console.log(`[api] fetchJournals ok ${data.items?.length ?? 0}/${data.total}`)
  return data
}

export async function saveJournal(payload, token) {
  console.log(`[api] saveJournal date=${payload.date} title=${payload.title?.slice(0, 30)}`)
  const response = await fetch(`${API_BASE}/devotion/journals`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify(payload),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Save journal failed')
  console.log(`[api] saveJournal ok id=${data.journal?.id}`)
  return data
}

export async function deleteJournal(journalId, token) {
  console.log(`[api] deleteJournal id=${journalId}`)
  const response = await fetch(`${API_BASE}/devotion/journals/${journalId}`, {
    method: 'DELETE',
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Delete journal failed')
  console.log(`[api] deleteJournal ok id=${journalId}`)
  return data
}

// ── Sermon Journal API ─────────────────────────────────────

export async function fetchSermonJournals(token, limit = 50, offset = 0) {
  console.log(`[api] fetchSermonJournals limit=${limit} offset=${offset}`)
  const response = await fetch(`${API_BASE}/sermon/journals?limit=${limit}&offset=${offset}`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Fetch sermon journals failed')
  console.log(`[api] fetchSermonJournals ok ${data.items?.length ?? 0}/${data.total}`)
  return data
}

export async function saveSermonJournal(payload, token) {
  console.log(`[api] saveSermonJournal date=${payload.date} title=${payload.title?.slice(0, 30)}`)
  const response = await fetch(`${API_BASE}/sermon/journals`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify(payload),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Save sermon journal failed')
  console.log(`[api] saveSermonJournal ok id=${data.journal?.id}`)
  return data
}

export async function deleteSermonJournal(journalId, token) {
  console.log(`[api] deleteSermonJournal id=${journalId}`)
  const response = await fetch(`${API_BASE}/sermon/journals/${journalId}`, {
    method: 'DELETE',
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Delete sermon journal failed')
  console.log(`[api] deleteSermonJournal ok id=${journalId}`)
  return data
}

// ── Personal Notes API (我的日记) ──────────────────────────

export async function fetchPersonalNotes(token) {
  console.log(`[api] fetchPersonalNotes`)
  const response = await fetch(`${API_BASE}/personal/notes`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Fetch personal notes failed')
  console.log(`[api] fetchPersonalNotes ok ${data.items?.length ?? 0}`)
  return data
}

export async function savePersonalNote(payload, token) {
  console.log(`[api] savePersonalNote id=${payload.id} date=${payload.date}`)
  const response = await fetch(`${API_BASE}/personal/notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify(payload),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Save personal note failed')
  console.log(`[api] savePersonalNote ok id=${data.note?.id}`)
  return data
}

export async function deletePersonalNote(noteId, token) {
  console.log(`[api] deletePersonalNote id=${noteId}`)
  const response = await fetch(`${API_BASE}/personal/notes/${noteId}`, {
    method: 'DELETE',
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Delete personal note failed')
  console.log(`[api] deletePersonalNote ok id=${noteId}`)
  return data
}

// ── User Profile API ─────────────────────────────────────────

export async function updateUserProfile(payload, token) {
  console.log(`[api] updateUserProfile nickname=${payload.nickname}`)
  const response = await fetch(`${API_BASE}/user/profile`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify(payload),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Update profile failed')
  console.log(`[api] updateUserProfile ok nickname=${data.nickname}`)
  return data
}

// ── Psychology Engine API (L0-L4) ────────────────────────────

export async function analyzePsychology(text, intensity = 5, includeHistory = true, token) {
  console.log(`[api] analyzePsychology intensity=${intensity}`)
  const response = await fetch(`${API_BASE}/psychology/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ text, intensity, include_history: includeHistory }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (response.ok === false && data.error) {
    throw new Error(data.error)
  }
  console.log(`[api] analyzePsychology completed`)
  return data
}

export async function fetchPsychologyDashboard(token) {
  console.log(`[api] fetchPsychologyDashboard`)
  const response = await fetch(`${API_BASE}/psychology/dashboard`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Failed to load dashboard')
  console.log(`[api] fetchPsychologyDashboard ok`)
  return data
}

export async function fetchBehavioralExperiments(status = 'all', limit = 20, token) {
  console.log(`[api] fetchBehavioralExperiments status=${status}`)
  const response = await fetch(`${API_BASE}/psychology/experiments?status=${status}&limit=${limit}`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Failed to load experiments')
  console.log(`[api] fetchBehavioralExperiments ok count=${data.items?.length || 0}`)
  return data
}

export async function completeBehavioralExperiment(experimentId, outcome, reflection, token) {
  console.log(`[api] completeBehavioralExperiment ${experimentId}`)
  const response = await fetch(`${API_BASE}/psychology/experiments/${experimentId}/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ experiment_id: experimentId, outcome, reflection }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Failed to complete experiment')
  console.log(`[api] completeBehavioralExperiment ok`)
  return data
}

export async function generateStory(emotion) {
  const response = await fetch(`${API_BASE}/story`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ emotion }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '故事生成失败')
  return data
}

// ── 行为调节系统 API ─────────────────────────────────────────

export async function regulateBehavior(task, energyLevel = 3, motivation = 5, token) {
  console.log(`[api] regulateBehavior energy=${energyLevel}`)
  const response = await fetch(`${API_BASE}/behavior/regulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ task, energy_level: energyLevel, motivation }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] regulateBehavior tier=${data.selected_tier}`)
  return data
}

// ── 习惯养成状态机 API ───────────────────────────────────────

export async function createHabit(habitName, anchor = '', energyLevel = 3, token) {
  console.log(`[api] createHabit name=${habitName}`)
  const response = await fetch(`${API_BASE}/habits/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ habit_name: habitName, anchor, energy_level: energyLevel }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '创建习惯失败')
  console.log(`[api] createHabit ok id=${data.saved_habit_id}`)
  return data
}

export async function fetchHabits(token) {
  console.log(`[api] fetchHabits`)
  const response = await fetch(`${API_BASE}/habits`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '获取习惯列表失败')
  console.log(`[api] fetchHabits ok count=${data.items?.length || 0}`)
  return data
}

export async function executeHabit(habitId, energyLevel = 3, token) {
  console.log(`[api] executeHabit ${habitId} energy=${energyLevel}`)
  const response = await fetch(`${API_BASE}/habits/${habitId}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ habit_id: habitId, energy_level: energyLevel }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '执行习惯失败')
  console.log(`[api] executeHabit tier=${data.selected_tier}`)
  return data
}

export async function logHabitExecution(habitId, tierExecuted, wasCompleted, completionPercentage, moodBefore, moodAfter, token) {
  console.log(`[api] logHabitExecution ${habitId} tier=${tierExecuted} completed=${wasCompleted}`)
  const response = await fetch(`${API_BASE}/habits/${habitId}/log`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ 
      habit_id: habitId, 
      tier_executed: tierExecuted,
      was_completed: wasCompleted,
      completion_percentage: completionPercentage,
      mood_before: moodBefore,
      mood_after: moodAfter
    }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '记录执行失败')
  console.log(`[api] logHabitExecution tokens=${data.tokens_earned}`)
  return data
}

export async function fetchHabitsDashboard(token) {
  console.log(`[api] fetchHabitsDashboard`)
  const response = await fetch(`${API_BASE}/habits/dashboard`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '获取仪表盘失败')
  console.log(`[api] fetchHabitsDashboard tokens=${data.token_balance}`)
  return data
}

// ── 执行力边缘引导系统 API ───────────────────────────────────

export async function detectExecutionParalysis(rawTask, edgeContext, telemetrySignals, token) {
  console.log(`[api] detectExecutionParalysis task=${rawTask.slice(0, 30)}...`)
  const response = await fetch(`${API_BASE}/execution/detect-intervene`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ raw_task: rawTask, edge_context: edgeContext, telemetry_signals: telemetrySignals }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] detectExecutionParalysis type=${data.paralysis_type} risk=${data.collapse_risk}`)
  return data
}

export async function generateMicroChain(task, steps = 3) {
  console.log(`[api] generateMicroChain steps=${steps}`)
  const response = await fetch(`${API_BASE}/execution/micro-chain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task, steps }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] generateMicroChain chain_length=${data.decoupled_chain?.length || 0}`)
  return data
}

export async function logIntervention(wasCompleted, completionPercentage, postInterventionMood, token) {
  console.log(`[api] logIntervention completed=${wasCompleted} mood=${postInterventionMood}`)
  const response = await fetch(`${API_BASE}/execution/log-intervention`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ was_completed: wasCompleted, completion_percentage: completionPercentage, post_intervention_mood: postInterventionMood }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] logIntervention momentum=${data.micro_momentum?.momentum_score}`)
  return data
}

export async function fetchExecutionDashboard(token) {
  console.log(`[api] fetchExecutionDashboard`)
  const response = await fetch(`${API_BASE}/execution/dashboard`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] fetchExecutionDashboard momentum=${data.current_momentum}`)
  return data
}

export async function fetchActiveMicroSessions(token) {
  console.log(`[api] fetchActiveMicroSessions`)
  const response = await fetch(`${API_BASE}/execution/active-sessions`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] fetchActiveMicroSessions count=${data.items?.length || 0}`)
  return data
}

// ── 身份认同重塑系统 API ───────────────────────────────────

export async function reinforceIdentity(recentBehaviors, emotionState, token) {
  console.log(`[api] reinforceIdentity behaviors=${recentBehaviors?.length || 0}`)
  const response = await fetch(`${API_BASE}/identity/reinforce`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ recent_behaviors: recentBehaviors, emotion_state: emotionState }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] reinforceIdentity narrative=${data.current_narrative?.slice(0, 30)}...`)
  return data
}

export async function deconstructLabel(negativeLabel, token) {
  console.log(`[api] deconstructLabel label=${negativeLabel}`)
  const response = await fetch(`${API_BASE}/identity/deconstruct`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ negative_label: negativeLabel }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] deconstructLabel distortion=${data.distortion_type}`)
  return data
}

export async function fetchIdentityDashboard(token) {
  console.log(`[api] fetchIdentityDashboard`)
  const response = await fetch(`${API_BASE}/identity/dashboard`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] fetchIdentityDashboard clarity=${data.identity_clarity}`)
  return data
}

// ── Personality OS 全局系统 API ───────────────────────────

export async function processWithPersonalityOS(userInput, telemetry, currentState, token) {
  console.log(`[api] processWithPersonalityOS state=${currentState}`)
  const response = await fetch(`${API_BASE}/os/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ user_input: userInput, telemetry, current_state: currentState }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] processWithPersonalityOS new_state=${data.system_state?.current_state}`)
  return data
}

export async function reportTelemetry(subsystem, telemetryData, token) {
  console.log(`[api] reportTelemetry subsystem=${subsystem}`)
  const response = await fetch(`${API_BASE}/os/telemetry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ subsystem, telemetry_data: telemetryData }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] reportTelemetry signals=${data.signals_generated}`)
  return data
}

export async function fetchPersonalityOSDashboard(token) {
  console.log(`[api] fetchPersonalityOSDashboard`)
  const response = await fetch(`${API_BASE}/os/dashboard`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] fetchPersonalityOSDashboard state=${data.current_state}`)
  return data
}

export async function setSystemState(newState, token) {
  console.log(`[api] setSystemState ${newState}`)
  const response = await fetch(`${API_BASE}/os/set-state`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ state: newState }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] setSystemState ok=${data.ok}`)
  return data
}

// ── 心理学分析面板 API ───────────────────────────────────

export async function analyzePsychology(emotionText, intensity, includeExperiments, token) {
  console.log(`[api] analyzePsychology intensity=${intensity}`)
  const response = await fetch(`${API_BASE}/psychology/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({
      emotion_text: emotionText,
      intensity: intensity,
      include_experiments: includeExperiments
    }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] analyzePsychology layers=${Object.keys(data.layers || {}).join(',')}`)
  return data
}

export async function fetchPsychologyDashboard(token) {
  console.log(`[api] fetchPsychologyDashboard`)
  const response = await fetch(`${API_BASE}/psychology/dashboard`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] fetchPsychologyDashboard logs=${data.total_logs}`)
  return data
}

export async function fetchBehavioralExperiments(status, limit, token) {
  console.log(`[api] fetchBehavioralExperiments status=${status}`)
  const response = await fetch(`${API_BASE}/behavior/experiments?status=${status}&limit=${limit || 10}`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] fetchBehavioralExperiments count=${data.items?.length || 0}`)
  return data
}

export async function completeBehavioralExperiment(expId, outcome, reflection, token) {
  console.log(`[api] completeBehavioralExperiment ${expId}`)
  const response = await fetch(`${API_BASE}/behavior/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({
      experiment_id: expId,
      outcome,
      reflection
    }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] completeBehavioralExperiment ok=${data.success}`)
  return data
}

// ── 执行力干预系统 API ───────────────────────────────────

export async function detectExecutionCrash(telemetry, token) {
  console.log(`[api] detectExecutionCrash`)
  const response = await fetch(`${API_BASE}/execution/crash-detect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({
      task_attempts: telemetry.task_attempts || 0,
      escape_urges: telemetry.escape_urges || 0,
      last_session_minutes: telemetry.last_session_minutes || 0
    }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] detectExecutionCrash detected=${data.detected} risk=${data.risk_score}`)
  return data
}

export async function generateIgnitionSequence(resistance, riskScore, token) {
  console.log(`[api] generateIgnitionSequence resistance=${resistance}`)
  const response = await fetch(`${API_BASE}/execution/ignite`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({
      resistance_type: resistance,
      current_risk_score: riskScore || 0.5
    }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] generateIgnitionSequence steps=${data.steps?.length}`)
  return data
}

export async function fetchMicroMomentum(token) {
  console.log(`[api] fetchMicroMomentum`)
  const response = await fetch(`${API_BASE}/execution/micro-momentum`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] fetchMicroMomentum score=${data.momentum_score}`)
  return data
}

export async function completeMicroSession(sessionId, outcome, reflection, token) {
  console.log(`[api] completeMicroSession ${sessionId}`)
  const response = await fetch(`${API_BASE}/execution/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({
      session_id: sessionId,
      outcome,
      reflection
    }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  console.log(`[api] completeMicroSession ok=${data.success}`)
  return data
}
