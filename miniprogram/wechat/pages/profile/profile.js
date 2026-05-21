const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    logged: false,
    userInfo: null,
    entitlements: null,
    orders: [],
    ordersTotal: 0,
    loading: false,
  },

  onShow() {
    this._refresh()
  },

  _refresh() {
    const token = app.globalData.token
    if (!token) {
      this.setData({ logged: false, entitlements: null, orders: [] })
      return
    }
    this.setData({ logged: true, loading: true, userInfo: app.globalData.userInfo })
    Promise.all([
      api.getEntitlements(),
      api.listOrders({ page: 1, page_size: 5 }),
    ])
      .then(([ent, ord]) => {
        this.setData({
          entitlements: ent,
          orders: ord.orders || [],
          ordersTotal: ord.total || 0,
        })
      })
      .catch((err) => {
        wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      })
      .finally(() => {
        this.setData({ loading: false })
      })
  },

  goLogin() {
    wx.navigateTo({ url: '/pages/login/login' })
  },

  goShop() {
    wx.switchTab({ url: '/pages/shop/shop' })
  },

  goOrders() {
    wx.navigateTo({ url: '/pages/orders/orders' })
  },

  onLogout() {
    wx.showModal({
      title: '确认退出',
      content: '退出后需要重新登录',
      confirmText: '退出',
      confirmColor: '#f5576c',
      success: ({ confirm }) => {
        if (!confirm) return
        api.logout().finally(() => {
          this.setData({ logged: false, entitlements: null, orders: [] })
          wx.showToast({ title: '已退出登录', icon: 'none' })
        })
      },
    })
  },

  cancelOrder(e) {
    const orderNo = e.currentTarget.dataset.orderno
    wx.showModal({
      title: '取消订单',
      content: '确定要取消该订单吗？',
      confirmColor: '#f5576c',
      success: ({ confirm }) => {
        if (!confirm) return
        api.cancelOrder(orderNo)
          .then(() => {
            wx.showToast({ title: '订单已取消', icon: 'success' })
            this._refresh()
          })
          .catch((err) => {
            wx.showToast({ title: err.message || '取消失败', icon: 'none' })
          })
      },
    })
  },

  statusLabel(status) {
    const map = {
      pending_payment: '待支付',
      paid:            '已支付',
      delivering:      '权益发放中',
      fulfilled:       '已完成',
      cancelled:       '已取消',
      refunding:       '退款中',
      refunded:        '已退款',
      payment_failed:  '支付失败',
    }
    return map[status] || status
  },
})
