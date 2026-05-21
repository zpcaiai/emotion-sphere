/**
 * utils/api.js — 小红书小程序统一 API 请求层（my.httpRequest）
 */

const app = getApp()

function request(method, path, data) {
  return new Promise((resolve, reject) => {
    const token = app.globalData.token
    const headers = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`

    const url = `${app.globalData.apiBase}${path}`

    my.httpRequest({
      url,
      method,
      headers,
      data: data ? JSON.stringify(data) : undefined,
      success(res) {
        if (res.status === 401) {
          app.globalData.token = null
          try { my.removeStorageSync({ key: 'token' }) } catch (e) {}
          my.navigateTo({ url: '/pages/login/login' })
          reject(new Error('未登录'))
          return
        }
        if (res.status >= 400) {
          const body = typeof res.data === 'string' ? JSON.parse(res.data) : (res.data || {})
          reject(new Error(body.detail || body.error || `HTTP ${res.status}`))
          return
        }
        const body = typeof res.data === 'string' ? JSON.parse(res.data) : (res.data || {})
        resolve(body)
      },
      fail(err) {
        reject(new Error((err && err.errorMessage) || '网络请求失败'))
      },
    })
  })
}

function buildUrl(path, params) {
  if (!params) return path
  const qs = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&')
  return qs ? `${path}?${qs}` : path
}

const get  = (path, params) => request('GET',  buildUrl(path, params), undefined)
const post = (path, data)   => request('POST', path, data)

// ── 认证 ─────────────────────────────────────────────────────────

/**
 * 小红书登录：my.getAuthCode → 后端换 token
 */
function xhsLogin() {
  return new Promise((resolve, reject) => {
    my.getAuthCode({
      scopes: ['auth_user'],
      success({ authCode }) {
        if (!authCode) { reject(new Error('获取授权码失败')); return }
        post('/auth/xhs-login', { code: authCode })
          .then((data) => {
            if (data && data.token) {
              app.globalData.token = data.token
              app.globalData.userInfo = data.user || {}
              try { my.setStorageSync({ key: 'token', data: data.token }) } catch (e) {}
            }
            resolve(data)
          })
          .catch(reject)
      },
      fail(err) { reject(new Error((err && err.errorMessage) || '授权失败')) },
    })
  })
}

function logout() {
  return post('/auth/logout', {}).finally(() => {
    app.globalData.token = null
    app.globalData.userInfo = null
    try { my.removeStorageSync({ key: 'token' }) } catch (e) {}
  })
}

function getMe() { return get('/auth/me') }

// ── 情绪 / 经文 ───────────────────────────────────────────────────

function fetchLayout() { return get('/layout') }

function queryVerses(query, opts) {
  return post('/query', {
    query,
    topFeatures: (opts && opts.topFeatures) || 5,
    topVerses:   (opts && opts.topVerses)   || 5,
    languageFilter: (opts && opts.languageFilter) || 'cuv',
  })
}

function fetchStory(emotion) { return post('/story', { emotion }) }

// ── 商城 ─────────────────────────────────────────────────────────

function listProducts(params) { return get('/shop/products', params) }
function getProduct(sku)       { return get(`/shop/products/${sku}`) }
function createOrder(payload)  { return post('/shop/orders', payload) }
function listOrders(params)    { return get('/shop/orders', params) }
function getOrder(orderNo)     { return get(`/shop/orders/${orderNo}`) }
function cancelOrder(orderNo, reason) {
  return post(`/shop/orders/${orderNo}/cancel`, { reason: reason || '用户主动取消' })
}
function getEntitlements()     { return get('/shop/entitlements') }
function getCreditsLedger(p)   { return get('/shop/credits/ledger', p) }
function queryWxPayOrder(orderNo) { return get(`/wxpay/orders/${orderNo}/query`) }

module.exports = {
  request, get, post,
  xhsLogin, logout, getMe,
  fetchLayout, queryVerses, fetchStory,
  listProducts, getProduct,
  createOrder, listOrders, getOrder, cancelOrder,
  getEntitlements, getCreditsLedger, queryWxPayOrder,
}
