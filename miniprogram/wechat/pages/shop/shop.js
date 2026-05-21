const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    products: [],
    loading: true,
    // 当前选中分类 tab
    activeTab: 'all',
    tabs: [
      { key: 'all',            label: '全部' },
      { key: 'credits',        label: '⭐ 星星币' },
      { key: 'subscription',   label: '👑 订阅' },
      { key: 'feature_unlock', label: '🔓 功能解锁' },
      { key: 'report',         label: '📊 报告' },
    ],
    // 支付弹窗
    payModal: false,
    payOrder: null,       // { order_no, pay_params, product_name }
    payPolling: false,
  },

  onLoad() {
    this._loadProducts()
  },

  onShow() {
    // 返回时刷新（防止下单后状态未更新）
    if (!this.data.loading) this._loadProducts()
  },

  _loadProducts(type) {
    this.setData({ loading: true })
    const params = type && type !== 'all' ? { product_type: type } : {}
    api.listProducts(params)
      .then((data) => {
        this.setData({ products: data.products || [] })
      })
      .catch((err) => {
        wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      })
      .finally(() => {
        this.setData({ loading: false })
      })
  },

  switchTab(e) {
    const key = e.currentTarget.dataset.key
    if (key === this.data.activeTab) return
    this.setData({ activeTab: key })
    this._loadProducts(key)
  },

  buyProduct(e) {
    if (!app.globalData.token) {
      wx.navigateTo({ url: '/pages/login/login' })
      return
    }
    const sku = e.currentTarget.dataset.sku
    const name = e.currentTarget.dataset.name

    wx.showLoading({ title: '创建订单…', mask: true })

    api.createOrder({ sku, quantity: 1, pay_method: 'miniprogram', platform: 'miniprogram' })
      .then((res) => {
        wx.hideLoading()
        if (!res.ok) {
          wx.showToast({ title: res.error || '创建订单失败', icon: 'none' })
          return
        }
        if (!res.pay_required) {
          // 免费商品直接到账
          wx.showToast({ title: '领取成功 🎉', icon: 'success' })
          return
        }
        // 需要微信支付
        this._invokePay(res.order_no, res.pay_params, name)
      })
      .catch((err) => {
        wx.hideLoading()
        wx.showToast({ title: err.message || '创建订单失败', icon: 'none' })
      })
  },

  _invokePay(orderNo, payParams, productName) {
    if (!payParams || !payParams.prepay_id) {
      wx.showToast({ title: '获取支付参数失败', icon: 'none' })
      return
    }
    wx.requestPayment({
      timeStamp: payParams.timeStamp,
      nonceStr:  payParams.nonceStr,
      package:   payParams.package,
      signType:  payParams.signType || 'RSA',
      paySign:   payParams.paySign,
      success: () => {
        // 支付成功后轮询订单状态（最多10次，每2秒）
        this._pollOrderStatus(orderNo, 0)
      },
      fail(err) {
        if (err.errMsg && err.errMsg.includes('cancel')) {
          wx.showToast({ title: '已取消支付', icon: 'none' })
        } else {
          wx.showToast({ title: '支付失败，请重试', icon: 'none' })
        }
      },
    })
  },

  _pollOrderStatus(orderNo, attempt) {
    if (attempt >= 10) {
      wx.showToast({ title: '支付确认中，请稍候', icon: 'none' })
      return
    }
    setTimeout(() => {
      api.queryWxPayOrder(orderNo)
        .then((res) => {
          if (res.status === 'fulfilled') {
            wx.showToast({ title: '购买成功 🎉', icon: 'success' })
          } else if (res.status === 'paid') {
            // 已支付等待履约，继续轮询
            this._pollOrderStatus(orderNo, attempt + 1)
          } else {
            this._pollOrderStatus(orderNo, attempt + 1)
          }
        })
        .catch(() => {
          this._pollOrderStatus(orderNo, attempt + 1)
        })
    }, 2000)
  },

  formatPrice(fen) {
    if (fen === 0) return '免费'
    return `¥${(fen / 100).toFixed(2)}`
  },
})
