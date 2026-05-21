const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    products: [],
    loading: true,
    activeTab: 'all',
    tabs: [
      { key: 'all',            label: '全部' },
      { key: 'credits',        label: '⭐ 星星币' },
      { key: 'subscription',   label: '👑 订阅' },
      { key: 'feature_unlock', label: '🔓 功能解锁' },
      { key: 'report',         label: '📊 报告' },
    ],
  },

  onLoad() {
    this._loadProducts()
  },

  onShow() {
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
        my.showToast({ content: err.message || '加载失败', type: 'none' })
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
      my.navigateTo({ url: '/pages/login/login' })
      return
    }
    const sku  = e.currentTarget.dataset.sku
    const name = e.currentTarget.dataset.name

    my.showLoading({ content: '创建订单…' })

    // 小红书小程序目前通过微信商户收款，pay_method=miniprogram
    // 若小红书平台接入独立支付，在此替换 pay_method
    api.createOrder({ sku, quantity: 1, pay_method: 'miniprogram', platform: 'xhs' })
      .then((res) => {
        my.hideLoading()
        if (!res.ok) {
          my.showToast({ content: res.error || '创建订单失败', type: 'none' })
          return
        }
        if (!res.pay_required) {
          my.showToast({ content: '领取成功 🎉', type: 'success' })
          return
        }
        // 小红书暂不支持原生微信支付调起，引导用户到 H5 收银台
        const h5Url = res.pay_params && res.pay_params.h5_url
        if (h5Url) {
          my.ap.navigateToAlipayPage({ path: h5Url }).catch(() => {
            my.showModal({
              title: '跳转支付',
              content: '即将跳转到支付页面，请完成支付后回到本页刷新订单状态。',
              confirmText: '去支付',
              success: ({ confirm }) => {
                if (confirm) {
                  my.loadFontFace  // no-op placeholder; actual H5 navigation below
                  // Fallback: copy link
                  my.showToast({ content: '请在浏览器中打开支付链接', type: 'none' })
                }
              },
            })
          })
        } else {
          my.showToast({ content: '订单已创建，请在「我的」中查看', type: 'none' })
        }
      })
      .catch((err) => {
        my.hideLoading()
        my.showToast({ content: err.message || '创建订单失败', type: 'none' })
      })
  },

  noop() {},
})
