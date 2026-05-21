/**
 * utils/api.js — 微信小程序统一 API 请求层
 * 自动携带 token、统一错误处理
 */

const app = getApp()

/**
 * 核心 request 封装，返回 Promise<responseData>
 */
function request(method, path, data) {
  return new Promise((resolve, reject) => {
    const token = app.globalData.token
    const header = { 'Content-Type': 'application/json' }
    if (token) header['Authorization'] = `Bearer ${token}`

    wx.request({
      url: `${app.globalData.apiBase}${path}`,
      method,
      header,
      data,
      success(res) {
        if (res.statusCode === 401) {
          // token 失效，清除并跳转登录
          app.globalData.token = null
          wx.removeStorageSync('token')
          wx.navigateTo({ url: '/pages/login/login' })
          reject(new Error('未登录'))
          return
        }
        if (res.statusCode >= 400) {
          const msg = (res.data && (res.data.detail || res.data.error)) || `HTTP ${res.statusCode}`
          reject(new Error(msg))
          return
        }
        resolve(res.data)
      },
      fail(err) {
        reject(new Error(err.errMsg || '网络请求失败'))
      },
    })
  })
}

const get  = (path, params) => request('GET',  buildUrl(path, params), undefined)
const post = (path, data)   => request('POST', path, data)

function buildUrl(path, params) {
  if (!params) return path
  const qs = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&')
  return qs ? `${path}?${qs}` : path
}

// ── 认证 ─────────────────────────────────────────────────────────

/**
 * 微信登录：获取 code → 后端换 session_key + token
 */
function wxLogin() {
  return new Promise((resolve, reject) => {
    wx.login({
      success({ code }) {
        if (!code) { reject(new Error('wx.login 获取 code 失败')); return }
        post('/auth/wxapp/login', { code })
          .then((data) => {
            if (data && data.token) {
              app.globalData.token = data.token
              app.globalData.userInfo = data.user || {}
              wx.setStorageSync('token', data.token)
            }
            resolve(data)
          })
          .catch(reject)
      },
      fail(err) { reject(new Error(err.errMsg || 'wx.login 失败')) },
    })
  })
}

function logout() {
  return post('/auth/logout', {}).finally(() => {
    app.globalData.token = null
    app.globalData.userInfo = null
    wx.removeStorageSync('token')
  })
}

function getMe() { return get('/auth/me') }

// ── 情绪 / 经文 ────────────────────────────────────────────────

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

// ── 商城 ────────────────────────────────────────────────────────

function listProducts(params) { return get('/shop/products', params) }

function getProduct(sku) { return get(`/shop/products/${sku}`) }

function createOrder(payload) { return post('/shop/orders', payload) }

function listOrders(params) { return get('/shop/orders', params) }

function getOrder(orderNo) { return get(`/shop/orders/${orderNo}`) }

function cancelOrder(orderNo, reason) {
  return post(`/shop/orders/${orderNo}/cancel`, { reason: reason || '用户主动取消' })
}

function getEntitlements() { return get('/shop/entitlements') }

function getCreditsLedger(params) { return get('/shop/credits/ledger', params) }

// 查询微信侧支付状态（前端轮询用）
function queryWxPayOrder(orderNo) { return get(`/wxpay/orders/${orderNo}/query`) }

// ── 导出 ────────────────────────────────────────────────────────

module.exports = {
  request, get, post,
  wxLogin, logout, getMe,
  fetchLayout, queryVerses, fetchStory,
  listProducts, getProduct,
  createOrder, listOrders, getOrder, cancelOrder,
  getEntitlements, getCreditsLedger, queryWxPayOrder,
}
