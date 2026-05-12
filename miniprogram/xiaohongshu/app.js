App({
  globalData: {
    userInfo: null,
    token: null,
    apiBase: 'https://stephenzao-emotion-sphere.hf.space/api',
  },
  onLaunch() {
    try {
      const token = my.getStorageSync({ key: 'token' }).data
      if (token) this.globalData.token = token
    } catch (e) {}
  },
})
