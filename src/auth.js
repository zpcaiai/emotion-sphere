import { API_BASE } from './api'

const TOKEN_KEY = 'bible-sphere-token'
const USER_KEY = 'bible-sphere-user'
const REMEMBERED_EMAIL_KEY = 'bible-sphere-remembered-email'
const REMEMBER_EMAIL_OPTION_KEY = 'bible-sphere-remember-email-option'
const BACKEND_DOWN_MSG = '后端服务不可用，请稍后重试'

const authUrl = (path) => `${API_BASE}/auth${path}`

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

// Remember email functions
export function getRememberedEmail() {
  return localStorage.getItem(REMEMBERED_EMAIL_KEY) || ''
}

export function setRememberedEmail(email) {
  if (email) {
    localStorage.setItem(REMEMBERED_EMAIL_KEY, email)
  } else {
    localStorage.removeItem(REMEMBERED_EMAIL_KEY)
  }
}

export function clearRememberedEmail() {
  localStorage.removeItem(REMEMBERED_EMAIL_KEY)
}

export function getRememberEmailOption() {
  return localStorage.getItem(REMEMBER_EMAIL_OPTION_KEY) === 'true'
}

export function setRememberEmailOption(remember) {
  localStorage.setItem(REMEMBER_EMAIL_OPTION_KEY, remember ? 'true' : 'false')
}

export function getCachedUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function setCachedUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export async function fetchCurrentUser() {
  const token = getToken()
  if (!token) return null
  try {
    const res = await fetch(authUrl('/me'), {
      headers: { Authorization: `Bearer ${token}` },
    })
    const contentType = res.headers.get('content-type') || ''
    if (!contentType.includes('application/json')) {
      throw new Error(BACKEND_DOWN_MSG)
    }
    if (!res.ok) {
      clearToken()
      return null
    }
    const data = await res.json()
    if (data.ok && data.user) {
      setCachedUser(data.user)
      return data.user
    }
    clearToken()
    return null
  } catch {
    return null
  }
}

export async function logout() {
  const token = getToken()
  if (token) {
    try {
      await fetch(authUrl('/logout'), {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
    } catch {
      // ignore
    }
  }
  clearToken()
}

export function redirectToWechatLogin() {
  window.location.href = authUrl('/wechat/login')
}

/**
 * Check if current browser is WeChat built-in browser
 */
export function isWechatBrowser() {
  return /MicroMessenger/i.test(navigator.userAgent)
}

/**
 * Check if current device is mobile
 */
export function isMobileDevice() {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
}

/**
 * Redirect to WeChat H5 OAuth for mobile (within WeChat app)
 * @param {Object} options
 * @param {string} options.scope - 'snsapi_base' (silent) or 'snsapi_userinfo' (with consent)
 * @param {string} options.frontendUrl - Optional custom frontend URL to redirect back
 */
export function redirectToWechatMobileLogin(options = {}) {
  const { scope = 'snsapi_userinfo', frontendUrl } = options
  const params = new URLSearchParams()
  params.set('scope', scope)
  params.set('redirect_type', 'mobile')
  if (frontendUrl) {
    params.set('frontend_url', frontendUrl)
  }
  window.location.href = `${authUrl('/wechat/mobile')}?${params.toString()}`
}

/**
 * Unified WeChat login - automatically detect PC or Mobile
 */
export function redirectToWechatLoginUnified(options = {}) {
  const { scope = 'snsapi_userinfo', frontendUrl } = options
  
  if (isWechatBrowser() || isMobileDevice()) {
    // Mobile/H5 flow (within WeChat app or mobile browser)
    redirectToWechatMobileLogin({ scope, frontendUrl })
  } else {
    // PC flow (QR code)
    redirectToWechatLogin()
  }
}

export async function sendEmailCode(email) {
  const res = await fetch(authUrl('/email/send-code'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  const contentType = res.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error(BACKEND_DOWN_MSG)
  }
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Failed to send code')
  // data may contain { dev_code: '123456' } when SMTP is not configured
  return data
}

export async function registerWithEmail(email, code, password, nickname = '') {
  const res = await fetch(authUrl('/email/register'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, code, password, nickname }),
  })
  const contentType = res.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error(BACKEND_DOWN_MSG)
  }
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Registration failed')
  if (data.token) {
    setToken(data.token)
    if (data.user) setCachedUser(data.user)
  }
  return data
}

export async function loginWithEmail(email, password) {
  const res = await fetch(authUrl('/email/login'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const contentType = res.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error(BACKEND_DOWN_MSG)
  }
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Login failed')
  if (data.token) {
    setToken(data.token)
    if (data.user) setCachedUser(data.user)
  }
  return data
}

export function extractTokenFromUrl() {
  const params = new URLSearchParams(window.location.search)
  const token = params.get('token')
  if (token) {
    setToken(token)
    // Clean up URL
    const url = new URL(window.location.href)
    url.searchParams.delete('token')
    window.history.replaceState({}, '', url.toString())
    return token
  }
  return null
}


export async function sendResetCode(email) {
  const res = await fetch(authUrl('/email/send-reset-code'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  const contentType = res.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error(BACKEND_DOWN_MSG)
  }
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Failed to send reset code')
  return data
}


export async function resetPassword(email, code, password) {
  const res = await fetch(authUrl('/email/reset-password'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, code, password }),
  })
  const contentType = res.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error(BACKEND_DOWN_MSG)
  }
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Password reset failed')
  return data
}

// ==================== WeChat Mini Program Login ====================

/**
 * Check if running inside WeChat Mini Program
 */
export function isWechatMiniProgram() {
  // wx object exists in WeChat Mini Program environment
  return typeof wx !== 'undefined' && wx.login && typeof wx.login === 'function'
}

/**
 * Login with WeChat Mini Program
 * This function should be called in WeChat Mini Program environment
 * @returns {Promise<{token: string, user: object}>}
 */
export async function loginWithWechatMiniProgram() {
  if (!isWechatMiniProgram()) {
    throw new Error('不在微信小程序环境中')
  }

  return new Promise((resolve, reject) => {
    wx.login({
      success: async (res) => {
        if (res.code) {
          try {
            // Send code to backend
            const response = await fetch(authUrl('/wechat/miniprogram/login'), {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ 
                code: res.code,
                appid: '' // Backend will use configured appid
              }),
            })
            
            const contentType = response.headers.get('content-type') || ''
            if (!contentType.includes('application/json')) {
              throw new Error(BACKEND_DOWN_MSG)
            }
            
            const data = await response.json()
            if (!response.ok) {
              throw new Error(data.detail || '微信小程序登录失败')
            }
            
            if (data.token) {
              setToken(data.token)
              if (data.user) setCachedUser(data.user)
            }
            
            resolve(data)
          } catch (err) {
            reject(err)
          }
        } else {
          reject(new Error(res.errMsg || '微信登录失败'))
        }
      },
      fail: (err) => {
        reject(new Error(err.errMsg || '微信登录调用失败'))
      }
    })
  })
}

/**
 * Get WeChat Mini Program user profile (nickname, avatar)
 * Requires user authorization in Mini Program
 * @returns {Promise<{nickName: string, avatarUrl: string, ...}>}
 */
export function getWechatMiniProgramUserProfile() {
  return new Promise((resolve, reject) => {
    if (!isWechatMiniProgram()) {
      reject(new Error('不在微信小程序环境中'))
      return
    }
    
    wx.getUserProfile({
      desc: '用于完善用户资料',
      success: (res) => {
        resolve(res.userInfo)
      },
      fail: (err) => {
        reject(new Error(err.errMsg || '获取用户信息失败'))
      }
    })
  })
}

/**
 * Update user info with Mini Program profile after login
 * @param {object} userInfo - From wx.getUserProfile
 */
export async function updateUserWithMiniProgramInfo(userInfo) {
  const token = getToken()
  if (!token) {
    throw new Error('未登录')
  }
  
  const res = await fetch(authUrl('/wechat/miniprogram/update-profile'), {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      nickname: userInfo.nickName,
      avatar: userInfo.avatarUrl,
      gender: userInfo.gender,
      city: userInfo.city,
      province: userInfo.province,
      country: userInfo.country
    }),
  })
  
  const contentType = res.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error(BACKEND_DOWN_MSG)
  }
  
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || '更新用户信息失败')
  
  // Update cached user
  if (data.user) {
    setCachedUser(data.user)
  }
  
  return data
}

/**
 * Unified login entry - automatically detect environment and choose appropriate method
 * @param {Object} options
 * @param {string} options.frontendUrl - Frontend URL for redirect
 * @returns {Promise<void>}
 */
export async function unifiedLogin(options = {}) {
  const { frontendUrl } = options
  
  if (isWechatMiniProgram()) {
    // WeChat Mini Program environment
    return loginWithWechatMiniProgram()
  } else if (isWechatBrowser()) {
    // WeChat built-in browser (mobile H5)
    redirectToWechatMobileLogin({ scope: 'snsapi_userinfo', frontendUrl })
    // Return a pending promise as page will redirect
    return new Promise(() => {})
  } else if (isMobileDevice()) {
    // Other mobile browser - use H5 or redirect to native app
    redirectToWechatMobileLogin({ scope: 'snsapi_userinfo', frontendUrl })
    return new Promise(() => {})
  } else {
    // PC - use QR code
    redirectToWechatLogin()
    return new Promise(() => {})
  }
}
