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
        my.showToast({ content: err.message || '加载失败', type: 'none' })
      })
      .finally(() => {
        this.setData({ loading: false })
      })
  },

  goLogin() {
    my.navigateTo({ url: '/pages/login/login' })
  },

  goShop() {
    my.switchTab({ url: '/pages/shop/shop' })
  },

  onLogout() {
    my.showModal({
      title: '确认退出',
      content: '退出后需要重新登录',
      confirmText: '退出',
      success: ({ confirm }) => {
        if (!confirm) return
        api.logout().finally(() => {
          this.setData({ logged: false, entitlements: null, orders: [] })
          my.showToast({ content: '已退出登录', type: 'none' })
        })
      },
    })
  },

  cancelOrder(e) {
    const orderNo = e.currentTarget.dataset.orderno
    my.showModal({
      title: '取消订单',
      content: '确定要取消该订单吗？',
      success: ({ confirm }) => {
        if (!confirm) return
        api.cancelOrder(orderNo)
          .then(() => {
            my.showToast({ content: '订单已取消', type: 'success' })
            this._refresh()
          })
          .catch((err) => {
            my.showToast({ content: err.message || '取消失败', type: 'none' })
          })
      },
    })
  },

  noop() {},
})
