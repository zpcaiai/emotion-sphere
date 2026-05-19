import { useEffect, useState } from 'react'
import { API_BASE } from './api'
import { getToken } from './auth'

const sfdsUrl = (path) => `${API_BASE}/sfds${path}`
const MVFE_BASE = API_BASE + '/mvfe'

const QUICK_PROMPTS = [
  {t:'最近工作压力很大，总是担心做不好，想逃避...',e:'😰',l:'焦虑逃避'},
  {t:'今天内心很平静，和家人一起很感恩...',e:'😌',l:'平静感恩'},
  {t:'感觉被忽视了，有点生气又不知道怎么表达...',e:'😤',l:'被忽视'},
  {t:'对未来充满期待，想尝试新的事情...',e:'✨',l:'充满期待'},
  {t:'一直在同一件事上反复纠结，走不出来...',e:'🔄',l:'反复纠结'},
]

// ==================== 现代生活决策类别（12大类，覆盖人生主要领域）====================
const decisionCategories = [
  // 职业与发展
  { value: 'career', label: '职业/工作', emoji: '💼', desc: '换工作、升职、创业、离职、职业规划' },
  { value: 'education', label: '教育/学习', emoji: '📚', desc: '升学、留学、进修、专业选择、技能学习' },
  { value: 'calling', label: '人生目标/使命', emoji: '🎯', desc: '人生方向、意义探索、使命确认' },
  
  // 人际关系
  { value: 'relationship', label: '人际关系', emoji: '💕', desc: '恋爱、婚姻、家庭、朋友、冲突处理' },
  { value: 'family', label: '家庭/亲子', emoji: '👨‍👩‍👧‍👦', desc: '育儿、夫妻关系、原生家庭、赡养老人' },
  { value: 'community', label: '社群/圈子', emoji: '👥', desc: '小组参与、圈子选择、分工协作、人际边界' },
  
  // 资源管理
  { value: 'financial', label: '财务/金钱', emoji: '💰', desc: '投资、消费、债务、储蓄、财务规划' },
  { value: 'housing', label: '居住/房产', emoji: '🏠', desc: '买房、租房、装修、搬家、选址' },
  { value: 'possessions', label: '物品/消费', emoji: '📱', desc: '大额消费、断舍离、购物诱惑、资产管理' },
  
  // 身心健康
  { value: 'health', label: '健康/身体', emoji: '🏥', desc: '就医、治疗、体检、生活方式改变' },
  { value: 'mental', label: '心理/情绪', emoji: '🧠', desc: '心理咨询、情绪管理、压力应对、休息安排' },
  
  // 内在成长与道德
  { value: 'temptation', label: '诱惑/考验', emoji: '⚠️', desc: '道德抉择、灰色地带、成瘾行为、冲动控制' },
  { value: 'spiritual', label: '心灵成长/修养', emoji: '🙏', desc: '冥想习惯、信念探索、内在平静、精神追求' },
  { value: 'ministry', label: '服务/志愿', emoji: '🤝', desc: '服务平衡、志愿角色、团队冲突、服务选择' },
  
  // 时间与生活方式
  { value: 'time', label: '时间/节奏', emoji: '⏰', desc: '工作与生活平衡、休息、优先级排序' },
  { value: 'lifestyle', label: '生活方式', emoji: '🌱', desc: '饮食习惯、运动、社交方式、数字健康' },
  { value: 'boundary', label: '边界/拒绝', emoji: '🚧', desc: '说"不"、设立界限、拒绝请求、保护自己' },
  
  // 危机与转变
  { value: 'crisis', label: '危机/急难', emoji: '🚨', desc: '突发事件、危机应对、紧急抉择' },
  { value: 'transition', label: '转变/过渡', emoji: '🌊', desc: '人生阶段转换、移民、退休、身份转变' },
  { value: 'loss', label: '失落/哀伤', emoji: '💔', desc: '分手、离别、失业、梦想破灭' },
  
  // 社会与文化
  { value: 'ethics', label: '伦理/正义', emoji: '⚖️', desc: '社会议题、公义行动、良心抉择、职场伦理' },
  { value: 'media', label: '媒体/信息', emoji: '📺', desc: '内容消费、社交媒体、新闻判断、网络行为' },
  { value: 'other', label: '其他/独特', emoji: '📝', desc: '无法归类、多重混合、独特处境' },
]

// ==================== 87个核心情绪（按情感星球分类）====================

// 正向情绪 — 渴望类 + 感恩类
const positiveEmotionsLonging = [
  { value: 'desire', label: '深切渴望', emoji: '💧', category: '内在渴望', en: 'desire' },
  { value: 'longing', label: '心灵向往', emoji: '💌', category: '精神思念', en: 'longing' },
  { value: 'reminiscence', label: '美好回忆', emoji: '📷', category: '感恩记忆', en: 'reminiscence' },
  { value: 'yearning', label: '热切期盼', emoji: '🌅', category: '未来希望', en: 'yearning' },
  { value: 'anticipation', label: '静静等待', emoji: '🎁', category: '耐心等候', en: 'anticipation' },
  { value: 'craving', label: '内在饥渴', emoji: '🔥', category: '成长渴望', en: 'craving' },
]

// 正向情绪 — 喜乐类 + 感恩类
const positiveEmotionsJoy = [
  { value: 'joy', label: '内心喜悦', emoji: '😊', category: '内在平和', en: 'joy' },
  { value: 'happiness', label: '幸福快乐', emoji: '😄', category: '生活满足', en: 'happiness' },
  { value: 'pleasure', label: '愉悦快乐', emoji: '😃', category: '享受当下', en: 'pleasure' },
  { value: 'gladness', label: '欣喜满足', emoji: '🙂', category: '满足之乐', en: 'gladness' },
  { value: 'bliss', label: '极乐宁静', emoji: '🥰', category: '深层幸福', en: 'bliss' },
  { value: 'gratitude', label: '感恩感谢', emoji: '🙏', category: '感恩心', en: 'gratitude' },
  { value: 'thankfulness', label: '感激不尽', emoji: '💝', category: '感恩之心', en: 'thankfulness' },
]

// 正向情绪 — 盼望类 + 热情类
const positiveEmotionsHope = [
  { value: 'hope', label: '充满希望', emoji: '🌟', category: '积极盼望', en: 'hope' },
  { value: 'optimism', label: '乐观向上', emoji: '☀️', category: '信心眼光', en: 'optimism' },
  { value: 'eagerness', label: '热心积极', emoji: '⚡', category: '积极热诚', en: 'eagerness' },
  { value: 'ardor', label: '热情如火', emoji: '🔥', category: '燃烧热情', en: 'ardor' },
  { value: 'fervor', label: '热忱投入', emoji: '✨', category: '专注投入', en: 'fervor' },
  { value: 'exuberance', label: '精力充沛', emoji: '🎉', category: '活力充沛', en: 'exuberance' },
  { value: 'excitement', label: '兴奋激动', emoji: '🤩', category: '激动期待', en: 'excitement' },
  { value: 'exhilaration', label: '欢欣鼓舞', emoji: '🥳', category: '欢欣振奋', en: 'exhilaration' },
  { value: 'rapture', label: '欣喜若狂', emoji: '😇', category: '极度喜悦', en: 'rapture' },
]

// 正向情绪 — 喜爱类 + 探索类
const positiveEmotionsLove = [
  { value: 'fascination', label: '深深吸引', emoji: '🤯', category: '被吸引', en: 'fascination' },
  { value: 'infatuation', label: '迷恋倾心', emoji: '💘', category: '倾慕', en: 'infatuation' },
  { value: 'fondness', label: '温柔喜爱', emoji: '🥺', category: '温柔情感', en: 'fondness' },
  { value: 'affection', label: '深情厚谊', emoji: '💕', category: '深厚情谊', en: 'affection' },
  { value: 'interest', label: '渴望求知', emoji: '👀', category: '求知好奇', en: 'interest' },
  { value: 'curiosity', label: '好奇探索', emoji: '🤔', category: '探索精神', en: 'curiosity' },
]

// 正向情绪 — 平静类 + 慰藉类
const positiveEmotionsCalm = [
  { value: 'invigoration', label: '精神焕发', emoji: '💪', category: '内在力量', en: 'invigoration' },
  { value: 'encouragement', label: '受到鼓励', emoji: '📈', category: '互相支持', en: 'encouragement' },
  { value: 'peace', label: '内心平静', emoji: '😌', category: '安宁', en: 'peace' },
  { value: 'tranquility', label: '宁静祥和', emoji: '🧘', category: '安静', en: 'tranquility' },
  { value: 'serenity', label: '神圣安宁', emoji: '🕊️', category: '深层宁静', en: 'serenity' },
  { value: 'security', label: '安全踏实', emoji: '🛡️', category: '安稳', en: 'security' },
]

// 正向情绪 — 释放类 + 自由类 + 满足类
const positiveEmotionsRelief = [
  { value: 'relief', label: '如释重负', emoji: '😮', category: '压力释放', en: 'relief' },
  { value: 'lightness', label: '轻松自在', emoji: '🎈', category: '卸下重担', en: 'lightness' },
  { value: 'comfort', label: '安慰慰藉', emoji: '🛋️', category: '内心安慰', en: 'comfort' },
  { value: 'enjoyment', label: '享受当下', emoji: '😋', category: '享受生活', en: 'enjoyment' },
  { value: 'fulfillment', label: '满足充实', emoji: '✅', category: '充实满足', en: 'fulfillment' },
  { value: 'satisfaction', label: '满意满足', emoji: '👍', category: '满意回报', en: 'satisfaction' },
]

// 负向情绪 — 孤独类
const negativeEmotionsLonely = [
  { value: 'loneliness', label: '孤独无依', emoji: '💔', category: '被遗弃感', en: 'loneliness' },
  { value: 'solitude', label: '独处寂寞', emoji: '🚶', category: '无人同行', en: 'solitude' },
  { value: 'isolation', label: '被孤立', emoji: '🏝️', category: '边缘化', en: 'isolation' },
  { value: 'hunger', label: '内心贫乏', emoji: '😣', category: '精神贫穷', en: 'hunger' },
]

// 负向情绪 — 悲伤类 + 绝望类
const negativeEmotionsSad = [
  { value: 'sadness', label: '悲伤难过', emoji: '😢', category: '哀伤', en: 'sadness' },
  { value: 'sorrow', label: '忧伤痛心', emoji: '😞', category: '内心痛苦', en: 'sorrow' },
  { value: 'grief', label: '悲痛欲绝', emoji: '😭', category: '深哀', en: 'grief' },
  { value: 'anguish', label: '极度痛苦', emoji: '💔', category: '极度难过', en: 'anguish' },
  { value: 'despair', label: '绝望无助', emoji: '🌑', category: '绝望', en: 'despair' },
  { value: 'hopelessness', label: '失去希望', emoji: '⚫', category: '无望', en: 'hopelessness' },
]

// 负向情绪 — 空虚类 + 懊悔类 + 自责类
const negativeEmotionsLoss = [
  { value: 'loss', label: '失落空虚', emoji: '📉', category: '失去感', en: 'loss' },
  { value: 'emptiness', label: '内心空洞', emoji: '🕳️', category: '空虚', en: 'emptiness' },
  { value: 'regret', label: '后悔遗憾', emoji: '😔', category: '后悔', en: 'regret' },
  { value: 'remorse', label: '悔恨交加', emoji: '😖', category: '懊悔', en: 'remorse' },
  { value: 'self_condemnation', label: '自我谴责', emoji: '💢', category: '自我批评', en: 'self-condemnation' },
]

// 负向情绪 — 羞愧类 + 内疚类
const negativeEmotionsShame = [
  { value: 'shame', label: '羞耻难堪', emoji: '🔴', category: '羞耻', en: 'shame' },
  { value: 'embarrassment', label: '尴尬窘迫', emoji: '😳', category: '窘迫', en: 'embarrassment' },
  { value: 'guilt', label: '内疚自责', emoji: '⛓️', category: '内疚', en: 'guilt' },
]

// 负向情绪 — 恐惧类 + 焦虑类
const negativeEmotionsFear = [
  { value: 'fear', label: '恐惧害怕', emoji: '😱', category: '敬畏/恐惧', en: 'fear' },
  { value: 'dread', label: '畏惧担忧', emoji: '😨', category: '惧怕', en: 'dread' },
  { value: 'anxiety', label: '焦虑不安', emoji: '😰', category: '忧虑', en: 'anxiety' },
  { value: 'worry', label: '担忧担心', emoji: '🤯', category: '担心', en: 'worry' },
  { value: 'nervousness', label: '紧张不安', emoji: '😬', category: '紧张', en: 'nervousness' },
  { value: 'panic', label: '惊慌失措', emoji: '😵', category: '惊慌', en: 'panic' },
]

// 负向情绪 — 愤怒类 + 厌恶类
const negativeEmotionsAnger = [
  { value: 'anger', label: '正当愤怒', emoji: '😠', category: '合理愤怒', en: 'anger' },
  { value: 'rage', label: '愤恨不平', emoji: '🤬', category: '愤恨', en: 'rage' },
  { value: 'fury', label: '暴怒失控', emoji: '😡', category: '失控', en: 'fury' },
  { value: 'irritation', label: '烦躁易怒', emoji: '😤', category: '不耐烦', en: 'irritation' },
  { value: 'impatience', label: '急躁不耐烦', emoji: '⏱️', category: '缺乏耐心', en: 'impatience' },
]

// 负向情绪 — 厌恶类 + 嫉妒类
const negativeEmotionsDisgust = [
  { value: 'disgust', label: '厌恶反感', emoji: '🤢', category: '厌恶', en: 'disgust' },
  { value: 'contempt', label: '鄙视轻蔑', emoji: '😒', category: '轻视', en: 'contempt' },
  { value: 'jealousy', label: '嫉妒吃醋', emoji: '😒', category: '嫉妒', en: 'jealousy' },
  { value: 'envy', label: '羡慕眼红', emoji: '👀', category: '羡慕', en: 'envy' },
]

// 复杂/关系情绪 — 同情类 + 理解类 + 宽恕类
const complexEmotionsCompassion = [
  { value: 'compassion', label: '慈悲心肠', emoji: '🧡', category: '怜悯心', en: 'compassion' },
  { value: 'sympathy', label: '同情体谅', emoji: '🤝', category: '同悲伤', en: 'sympathy' },
  { value: 'empathy', label: '同理共情', emoji: '💜', category: '体会', en: 'empathy' },
  { value: 'comprehension', label: '领悟明白', emoji: '💡', category: '理解', en: 'comprehension' },
  { value: 'forgiveness', label: '宽恕原谅', emoji: '🕊️', category: '释放', en: 'forgiveness' },
  { value: 'pardon', label: '白白饶恕', emoji: '✨', category: '被宽恕', en: 'pardon' },
]

// 复杂/关系情绪 — 矛盾类 + 迷茫类 + 疑惑类 + 防备类 + 疏离类
const complexEmotionsAmbivalence = [
  { value: 'ambivalence', label: '矛盾纠结', emoji: '⚖️', category: '内心冲突', en: 'ambivalence' },
  { value: 'confusion', label: '困惑迷茫', emoji: '🌫️', category: '迷失', en: 'confusion' },
  { value: 'uncertainty', label: '不确定感', emoji: '❓', category: '未知', en: 'uncertainty' },
  { value: 'doubt', label: '怀疑疑虑', emoji: '🤔', category: '质疑', en: 'doubt' },
  { value: 'defensiveness', label: '防御自卫', emoji: '🛡️', category: '防备', en: 'defensiveness' },
  { value: 'alienation', label: '疏离隔绝', emoji: '🧱', category: '被隔绝', en: 'alienation' },
]

// 完整情绪列表（87个）
const emotionTypes = [
  ...positiveEmotionsLonging,
  ...positiveEmotionsJoy,
  ...positiveEmotionsHope,
  ...positiveEmotionsLove,
  ...positiveEmotionsCalm,
  ...positiveEmotionsRelief,
  ...negativeEmotionsLonely,
  ...negativeEmotionsSad,
  ...negativeEmotionsLoss,
  ...negativeEmotionsShame,
  ...negativeEmotionsFear,
  ...negativeEmotionsAnger,
  ...negativeEmotionsDisgust,
  ...complexEmotionsCompassion,
  ...complexEmotionsAmbivalence,
]

// 情绪分类导航（用于UI展示）
const emotionCategories = [
  { key: 'longing', label: '渴望与盼望', emotions: [...positiveEmotionsLonging, ...positiveEmotionsHope.filter(e => e.category === '盼望类')] },
  { key: 'joy', label: '快乐与感激', emotions: positiveEmotionsJoy },
  { key: 'passion', label: '热情与兴奋', emotions: positiveEmotionsHope.filter(e => ['热情类', '兴奋类', '陶醉类'].includes(e.category)) },
  { key: 'love', label: '喜爱与好奇', emotions: positiveEmotionsLove },
  { key: 'calm', label: '平静与安宁', emotions: [...positiveEmotionsCalm, ...positiveEmotionsRelief] },
  { key: 'lonely', label: '孤独与失落', emotions: [...negativeEmotionsLonely, ...negativeEmotionsLoss] },
  { key: 'sad', label: '悲伤与绝望', emotions: negativeEmotionsSad },
  { key: 'shame', label: '羞愧与内疚', emotions: negativeEmotionsShame },
  { key: 'fear', label: '恐惧与焦虑', emotions: negativeEmotionsFear },
  { key: 'anger', label: '愤怒与厌恶', emotions: [...negativeEmotionsAnger, ...negativeEmotionsDisgust] },
  { key: 'complex', label: '复杂与关系', emotions: [...complexEmotionsCompassion, ...complexEmotionsAmbivalence] },
]

// 内在智慧原则（去宗教化版本）
const wisdomPrinciples = [
  { id: '1', text: '凡事察验，善美的要持守', ref: '智慧格言' },
  { id: '2', text: '你要保守你心，胜过保守一切', ref: '内心守护' },
  { id: '3', text: '不要恐惧，因为我与你同在', ref: '勇气支持' },
  { id: '4', text: '看别人比自己强', ref: '谦逊智慧' },
  { id: '5', text: '凭果子认出他们来', ref: '结果验证' },
  { id: '6', text: '爱比成功更高', ref: '爱的优先' },
  { id: '7', text: '真理比舒适更重要', ref: '真实勇气' },
  { id: '8', text: '谦卑在智慧以先', ref: '谦逊智慧' },
  { id: '9', text: '安息是内在操练', ref: '休息重要' },
  { id: '10', text: '听从良知，不随波逐流', ref: '独立判断' },
  { id: '11', text: '愿意受苦而不愿违背良知', ref: '坚守原则' },
  { id: '12', text: '患难生忍耐，忍耐生老练', ref: '成长历练' },
  { id: '13', text: '不为明天忧虑', ref: '活在当下' },
  { id: '14', text: '在压力中保持平静', ref: '内在平静' },
  { id: '15', text: '不可为恶所胜，反要以善胜恶', ref: '善胜恶' },
]

export default function DecisionSupportPage({ user, onBack, onDashboard, embedded = false }) {
  const [activeTab, setActiveTab] = useState('new') // new, history, principles
  const [loading, setLoading] = useState(false)
  const [decisions, setDecisions] = useState([])
  const [selectedDecision, setSelectedDecision] = useState(null)
  
  // ==================== 用户个人标签系统 ====================
  const [userTags, setUserTags] = useState([])
  const [tagInsights, setTagInsights] = useState(null)
  const [tagsLoading, setTagsLoading] = useState(false)

  // ==================== 扩展状态快照（12维度，覆盖身心灵社智财道）====================
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category: '',
    urgency: 3,
    importance: 3,
    // 原始5维度（保留兼容）
    stressLevel: 5,          // 压力水平
    anxietyLevel: 5,         // 焦虑水平
    fatigueLevel: 5,         // 疲劳程度
    spiritualDryness: 5,     // 精神干涸 → 改为内心枯竭
    emotionalStability: 5,   // 情绪稳定
    // 扩展7维度（现代生活完整画像）
    physicalHealth: 5,       // 身体健康
    sleepQuality: 5,         // 睡眠质量
    socialConnection: 5,     // 社交连接
    financialPressure: 5,    // 财务压力
    cognitiveClarity: 5,      // 认知清晰度
    identityConfusion: 5,    // 身份困惑
    moralTension: 5,         // 道德张力
    emotions: [],
  })

  // 灵镜分析 + 结果展示
  const [analysisResult, setAnalysisResult] = useState(null)
  const [mvfeResult, setMvfeResult] = useState(null)
  const [mvfeProcessing, setMvfeProcessing] = useState(false)
  const [mvfeError, setMvfeError] = useState('')
  const userId = String(user?.id || user?.email || 'default_user')

  // 加载决策历史
  useEffect(() => {
    if (activeTab === 'history') {
      loadDecisions()
    }
  }, [activeTab])
  
  // 加载用户标签
  useEffect(() => {
    if (user?.id || user?.userId) {
      loadUserTags()
    }
  }, [user])
  
  const loadUserTags = async () => {
    const userId = user?.id || user?.userId
    if (!userId) return
    
    setTagsLoading(true)
    try {
      const res = await fetch(`${API_BASE}/user-tags/${userId}?include_insights=true&limit=20`, {
        headers: { Authorization: `Bearer ${getToken()}` }
      })
      if (res.ok) {
        const data = await res.json()
        setUserTags(data.tags || [])
        setTagInsights(data.insights || null)
      }
    } catch (err) {
      console.log('[DecisionSupport] load user tags failed:', err)
    } finally {
      setTagsLoading(false)
    }
  }
  
  // 渲染用户标签组件
  const renderUserTags = () => {
    if (tagsLoading || userTags.length === 0) return null
    
    // 按分类分组
    const tagsByCategory = userTags.reduce((acc, tag) => {
      const cat = tag.tag_category || '其他'
      if (!acc[cat]) acc[cat] = []
      acc[cat].push(tag)
      return acc
    }, {})
    
    // 分类中文映射
    const categoryNames = {
      'emotion_type': '情绪特征',
      'life_domain': '生活领域',
      'behavior': '行为模式',
      'value': '价值观',
      'relationship': '关系模式',
      'spiritual': '精神成长',
      'cognitive': '认知风格',
      'decision': '决策风格',
      'manual': '手动添加',
      'unknown': '其他'
    }
    
    // 分类颜色
    const categoryColors = {
      'emotion_type': '#ff6b6b',
      'life_domain': '#4ecdc4',
      'behavior': '#ffe66d',
      'value': '#95e1d3',
      'relationship': '#f38181',
      'spiritual': '#aa96da',
      'cognitive': '#fcbad3',
      'decision': '#ffffd2',
      'manual': '#a8e6cf',
      'unknown': '#aaa'
    }
    
    return (
      <div style={{
        margin: '16px',
        padding: '16px',
        borderRadius: '12px',
        background: 'rgba(255,255,255,0.05)',
        border: '1px solid rgba(255,255,255,0.1)',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '12px',
        }}>
          <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>
            🏷️ 我的个人标签
          </div>
          {tagInsights && (
            <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)' }}>
              共 {tagInsights.total_tags} 个标签 · {tagInsights.total_categories} 个维度
            </div>
          )}
        </div>
        
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {userTags.slice(0, 15).map((tag, idx) => {
            const color = categoryColors[tag.tag_category] || '#aaa'
            const weight = tag.weight || 1
            const opacity = Math.min(0.3 + (weight * 0.15), 0.9)
            
            return (
              <div
                key={tag.id || idx}
                style={{
                  padding: '4px 10px',
                  borderRadius: '16px',
                  background: `${color}${Math.round(opacity * 255).toString(16).padStart(2, '0')}`,
                  color: '#fff',
                  fontSize: '12px',
                  border: `1px solid ${color}40`,
                  cursor: 'default',
                  transition: 'all 0.2s',
                }}
                title={`${categoryNames[tag.tag_category] || tag.tag_category} · 权重: ${tag.weight?.toFixed(2) || 1} · 出现: ${tag.occurrence_count || 1}次`}
              >
                {tag.tag_name}
              </div>
            )
          })}
        </div>
        
        {userTags.length > 15 && (
          <div style={{ 
            marginTop: '8px', 
            fontSize: '11px', 
            color: 'rgba(255,255,255,0.4)',
            textAlign: 'center'
          }}>
            +{userTags.length - 15} 更多标签
          </div>
        )}
      </div>
    )
  }

  const loadDecisions = async () => {
    try {
      const token = getToken()
      const res = await fetch(sfdsUrl('/decisions') + '?user_id=' + encodeURIComponent(userId), {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('加载失败')
      const data = await res.json()
      setDecisions(data)
    } catch (err) {
      console.error('加载决策历史失败:', err)
    }
  }

  // 灵镜分析 — 调用 MVFE /process, 并自动触发内在辨识
  const handleMvfeAnalysis = async (text, autoSubmit = true) => {
    const t = text || formData.description
    if (!t.trim()) return null
    setMvfeProcessing(true); setMvfeError('')
    try {
      const r = await fetch(MVFE_BASE + '/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: t, user_id: userId }),
      })
      const respText = await r.text()
      if (!r.ok) {
        let msg = '灵镜分析失败'
        try {
          const j = JSON.parse(respText)
          msg = j.detail || j.error || msg
        } catch {}
        throw new Error(msg)
      }
      const d = JSON.parse(respText)
      setMvfeResult(d)
      // Auto-map MVFE results to decision form emotion/state fields
      autoMapMvfeToForm(d)
      
      // 自动触发内在辨识（如果表单已填写完整）
      if (autoSubmit) {
        // 使用 setTimeout 确保 state 更新完成
        setTimeout(() => {
          submitDiscernment(d)
        }, 100)
      }
      
      return d
    } catch (err) {
      setMvfeError(err.message)
      return null
    } finally {
      setMvfeProcessing(false)
    }
  }
  
  // 提交内在辨识（从 handleSubmit 提取的独立函数）
  const submitDiscernment = async (mvfeData) => {
    // 检查必填字段
    if (!formData.title || !formData.category) {
      // 如果缺少必填字段，只显示分析结果，不自动提交
      console.log('[DecisionSupport] 缺少标题或类别，跳过自动提交')
      return
    }
    
    setLoading(true)
    try {
      const token = getToken()
      
      // 使用最新 formData 构建提交数据
      const latestForm = formData
      
      const payload = {
        title: latestForm.title,
        description: latestForm.description,
        category: latestForm.category,
        urgency: latestForm.urgency,
        importance: latestForm.importance,
        state_snapshot: {
          stress_level: latestForm.stressLevel,
          anxiety_level: latestForm.anxietyLevel,
          fatigue_level: latestForm.fatigueLevel,
          spiritual_dryness: latestForm.spiritualDryness,
          emotional_stability: latestForm.emotionalStability,
          physical_health: latestForm.physicalHealth,
          sleep_quality: latestForm.sleepQuality,
          social_connection: latestForm.socialConnection,
          financial_pressure: latestForm.financialPressure,
          cognitive_clarity: latestForm.cognitiveClarity,
          identity_confusion: latestForm.identityConfusion,
          moral_tension: latestForm.moralTension,
        },
        emotion_logs: latestForm.emotions.map((e, i) => ({
          emotion_type: e.type,
          intensity: e.intensity,
          trigger: e.trigger,
          timestamp: new Date(Date.now() - i * 60000).toISOString(),
        })),
        context_factors: {
          user_note: latestForm.description,
          mvfe_event_id: mvfeData?.event_id || null,
        },
      }
      
      const res = await fetch(sfdsUrl('/decisions') + '?user_id=' + encodeURIComponent(userId), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      })
      
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || '提交失败')
      }
      
      const result = await res.json()
      
      // 等待分析完成（轮询）
      await pollForAnalysis(result.id)
      
    } catch (err) {
      // 静默失败，不打扰用户，只记录日志
      console.log('[DecisionSupport] 自动辨识未启动:', err.message)
    } finally {
      setLoading(false)
    }
  }

  // 自动从 MVFE 分析结果映射到决策表单
  const autoMapMvfeToForm = (mvfe) => {
    if (!mvfe) return
    const em = mvfe.emotion || {}
    const at = mvfe.attention || {}
    const fo = mvfe.formation || {}
    const dc = mvfe.decision || {}

    const emotionToStress = { anxiety:8, fear:7, anger:7, sadness:6, guilt:6, shame:6, joy:2, peace:1, hope:2, love:2, gratitude:1, envy:5, loneliness:6, disgust:4, surprise:3 }
    const emotionToAnxiety = { anxiety:9, fear:8, anger:5, sadness:5, guilt:6, shame:6, joy:1, peace:1, hope:2, love:2, gratitude:1, envy:4, loneliness:5, disgust:3, surprise:4 }
    const emotionToSpiritual = { anxiety:6, fear:5, anger:5, sadness:7, guilt:8, shame:8, joy:2, peace:1, hope:2, love:2, gratitude:1, envy:5, loneliness:6, disgust:4, surprise:3 }

    const primary = em.primary_emotion || 'unknown'
    const intensity = em.intensity || 0.5
    const stress = Math.round((emotionToStress[primary] || 5) * intensity + 5 * (1 - intensity))
    const anxiety = Math.round((emotionToAnxiety[primary] || 5) * intensity + 5 * (1 - intensity))
    const spiritualDry = Math.round((emotionToSpiritual[primary] || 5) * intensity + 5 * (1 - intensity))
    const stability = Math.round((fo.stability_score || 0.5) * 10)
    const fatigue = Math.round((at.fixation_score || 0.5) * 8 + 1)

    const emotions = [{ type: primary, intensity: Math.round(intensity * 10), trigger: at.anchor_object || '' }]
    if (em.secondary_emotions?.length > 0) {
      em.secondary_emotions.slice(0, 2).forEach(sec => {
        emotions.push({ type: sec, intensity: Math.round(intensity * 10 * 0.6), trigger: '' })
      })
    }

    setFormData(prev => ({
      ...prev,
      // 基础维度映射
      stressLevel: stress,
      anxietyLevel: anxiety,
      fatigueLevel: fatigue,
      spiritualDryness: spiritualDry,
      emotionalStability: stability,
      // 扩展维度映射（从MVFE formation和context推断）
      physicalHealth: Math.round(10 - (fo.formation_score ? (1 - fo.formation_score) * 5 : 2.5)),
      sleepQuality: Math.round(10 - fatigue * 0.6 - stress * 0.3),
      socialConnection: at.social_context === 'isolated' ? 3 : (at.social_context === 'supportive' ? 8 : 5),
      financialPressure: dc?.drivers?.ego > 0.6 ? 7 : (dc?.drivers?.fear > 0.6 ? 6 : 4),
      cognitiveClarity: 10 - Math.round((em.uncertainty || 0.3) * 10),
      identityConfusion: em.secondary_emotions?.includes('confusion') ? 7 : (at.fixation_score > 0.7 ? 6 : 4),
      moralTension: dc?.drivers?.love < 0.3 && dc?.drivers?.ego > 0.5 ? 6 : 4,
      emotions,
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      const token = getToken()

      // 如果还没有进行灵镜分析，先执行一次并等待映射完成
      let currentMvfe = mvfeResult
      if (!currentMvfe && formData.description.trim()) {
        currentMvfe = await handleMvfeAnalysis(formData.description)
      }

      // 使用已映射的 formData（autoMapMvfeToForm 已更新），或读取最新 state
      // 注意：autoMapMvfeToForm 通过 setFormData 更新，此处需要用回调读取最新值
      const latestForm = await new Promise(resolve => {
        setFormData(prev => { resolve(prev); return prev })
      })

      // 构建提交数据
      const payload = {
        title: latestForm.title,
        description: latestForm.description,
        category: latestForm.category,
        urgency: latestForm.urgency,
        importance: latestForm.importance,
        state_snapshot: {
          // 原始5维度
          stress_level: latestForm.stressLevel,
          anxiety_level: latestForm.anxietyLevel,
          fatigue_level: latestForm.fatigueLevel,
          spiritual_dryness: latestForm.spiritualDryness,
          emotional_stability: latestForm.emotionalStability,
          // 扩展7维度
          physical_health: latestForm.physicalHealth,
          sleep_quality: latestForm.sleepQuality,
          social_connection: latestForm.socialConnection,
          financial_pressure: latestForm.financialPressure,
          cognitive_clarity: latestForm.cognitiveClarity,
          identity_confusion: latestForm.identityConfusion,
          moral_tension: latestForm.moralTension,
        },
        emotion_logs: latestForm.emotions.map((e, i) => ({
          emotion_type: e.type,
          intensity: e.intensity,
          trigger: e.trigger,
          timestamp: new Date(Date.now() - i * 60000).toISOString(),
        })),
        context_factors: {
          user_note: latestForm.description,
          mvfe_event_id: currentMvfe?.event_id || null,
        },
      }

      const res = await fetch(sfdsUrl('/decisions') + '?user_id=' + encodeURIComponent(userId), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || '提交失败')
      }

      const result = await res.json()
      
      // 等待分析完成（轮询）
      await pollForAnalysis(result.id)
      
    } catch (err) {
      alert(err.message)
    } finally {
      setLoading(false)
    }
  }

  const pollForAnalysis = async (decisionId) => {
    const token = getToken()
    let attempts = 0
    const maxAttempts = 30 // 最多等待30秒

    while (attempts < maxAttempts) {
      const res = await fetch(sfdsUrl(`/decisions/${decisionId}`) + '?user_id=' + encodeURIComponent(userId), {
        headers: { Authorization: `Bearer ${token}` },
      })
      
      if (res.ok) {
        const data = await res.json()
        
        if (data.status === 'guided' && data.guidance) {
          setAnalysisResult(data)
          return
        }
        
        if (data.status === 'analyzing') {
          await new Promise(r => setTimeout(r, 1000))
          attempts++
          continue
        }
      }
      
      break
    }
  }

  const addEmotion = () => {
    setFormData(prev => ({
      ...prev,
      emotions: [...prev.emotions, { type: '', intensity: 5, trigger: '' }],
    }))
  }

  const updateEmotion = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      emotions: prev.emotions.map((e, i) => 
        i === index ? { ...e, [field]: value } : e
      ),
    }))
  }

  const removeEmotion = (index) => {
    setFormData(prev => ({
      ...prev,
      emotions: prev.emotions.filter((_, i) => i !== index),
    }))
  }

  // 渲染导航标签
  const renderTabs = () => (
    <div style={{
      display: 'flex',
      gap: '8px',
      padding: '12px 16px',
      borderBottom: '1px solid rgba(255,255,255,0.1)',
      background: 'rgba(28,28,30,0.8)',
      position: 'sticky',
      top: 0,
      zIndex: 10,
    }}>
      {[
        { key: 'new', label: '新决策', emoji: '🆕' },
        { key: 'history', label: '历史', emoji: '📜' },
        { key: 'principles', label: '原则', emoji: '📖' },
      ].map(tab => (
        <button
          key={tab.key}
          onClick={() => {
            setActiveTab(tab.key)
            setAnalysisResult(null)
          }}
          style={{
            flex: 1,
            padding: '10px 12px',
            borderRadius: '10px',
            border: 'none',
            background: activeTab === tab.key ? '#007aff' : 'rgba(120,120,128,0.2)',
            color: activeTab === tab.key ? '#fff' : 'rgba(255,255,255,0.6)',
            fontSize: '14px',
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '4px',
          }}
        >
          <span>{tab.emoji}</span>
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  )

  // 渲染新决策表单
  const renderNewDecisionForm = () => (
    <>
    <form id="decision-form" onSubmit={handleSubmit} style={{ padding: '16px' }}>
      {/* 决策标题 */}
      <div style={{ marginBottom: '16px' }}>
        <label style={labelStyle}>决策标题 *</label>
        <input
          type="text"
          value={formData.title}
          onChange={e => setFormData(prev => ({ ...prev, title: e.target.value }))}
          placeholder="例如：是否应该接受这份工作邀请？"
          style={inputStyle}
          required
        />
      </div>

      {/* 决策类别 */}
      <div style={{ marginBottom: '16px' }}>
        <label style={labelStyle}>决策类别 *</label>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {decisionCategories.map(cat => (
            <button
              key={cat.value}
              type="button"
              onClick={() => setFormData(prev => ({ ...prev, category: cat.value }))}
              style={{
                padding: '8px 12px',
                borderRadius: '20px',
                border: formData.category === cat.value ? '2px solid #007aff' : '1px solid rgba(255,255,255,0.2)',
                background: formData.category === cat.value ? 'rgba(0,122,255,0.2)' : 'rgba(255,255,255,0.05)',
                color: '#fff',
                fontSize: '13px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span>{cat.emoji}</span>
              <span>{cat.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 紧急与重要程度 */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
        <div style={{ flex: 1 }}>
          <label style={labelStyle}>紧急程度: {formData.urgency}/5</label>
          <input
            type="range"
            min="1"
            max="5"
            value={formData.urgency}
            onChange={e => setFormData(prev => ({ ...prev, urgency: parseInt(e.target.value) }))}
            style={{ width: '100%' }}
          />
        </div>
        <div style={{ flex: 1 }}>
          <label style={labelStyle}>重要程度: {formData.importance}/5</label>
          <input
            type="range"
            min="1"
            max="5"
            value={formData.importance}
            onChange={e => setFormData(prev => ({ ...prev, importance: parseInt(e.target.value) }))}
            style={{ width: '100%' }}
          />
        </div>
      </div>

      {/* 当前状态快照 */}
      <div style={{ 
        background: 'rgba(0,122,255,0.1)', 
        borderRadius: '12px', 
        padding: '16px',
        marginBottom: '16px',
      }}>
        <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px', color: '#007aff' }}>
          🔍 当前状态快照
        </div>
        
        {/* 原始5维度 — 基础身心灵状态 */}
        <div style={{ fontSize: '12px', color: '#007aff', marginBottom: '8px', fontWeight: 500 }}>
          📊 基础维度（身心核心）
        </div>
        {[
          { key: 'stressLevel', label: '压力水平', icon: '😰', desc: '外部要求与内部资源的差距' },
          { key: 'anxietyLevel', label: '焦虑水平', icon: '😨', desc: '对未来不确定的担忧程度' },
          { key: 'fatigueLevel', label: '疲劳程度', icon: '😴', desc: '身心能量耗竭的感受' },
          { key: 'spiritualDryness', label: '内心枯竭', icon: '🏜️', desc: '与内在自我连接的感受减弱' },
          { key: 'emotionalStability', label: '情绪稳定', icon: '😌', desc: '情绪波动的可控程度' },
        ].map(item => (
          <div key={item.key} style={{ marginBottom: '10px' }}>
            <label style={{ ...labelStyle, fontSize: '13px' }}>
              {item.icon} {item.label}: {formData[item.key]}/10
              <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', marginLeft: '8px' }}>
                {item.desc}
              </span>
            </label>
            <input
              type="range"
              min="0"
              max="10"
              value={formData[item.key]}
              onChange={e => setFormData(prev => ({ ...prev, [item.key]: parseInt(e.target.value) }))}
              style={{ width: '100%' }}
            />
          </div>
        ))}
        
        {/* 扩展7维度 — 现代生活完整画像 */}
        <div style={{ fontSize: '12px', color: '#34c759', margin: '16px 0 8px', fontWeight: 500 }}>
          🌐 扩展维度（现代生活全景）
        </div>
        {[
          { key: 'physicalHealth', label: '身体健康', icon: '💪', desc: '身体状况与精力水平', color: '#34c759' },
          { key: 'sleepQuality', label: '睡眠质量', icon: '🌙', desc: '休息恢复与睡眠满意度', color: '#af52de' },
          { key: 'socialConnection', label: '社交连接', icon: '🤝', desc: '关系网络与支持系统', color: '#007aff' },
          { key: 'financialPressure', label: '财务压力', icon: '💰', desc: '经济焦虑与资源担忧', color: '#ff9500' },
          { key: 'cognitiveClarity', label: '认知清晰', icon: '🧠', desc: '思维清晰度与专注力', color: '#5ac8fa' },
          { key: 'identityConfusion', label: '身份困惑', icon: '❓', desc: '自我认知与定位迷茫', color: '#ff3b30' },
          { key: 'moralTension', label: '道德张力', icon: '⚖️', desc: '价值观冲突与良心挣扎', color: '#ffcc00' },
        ].map(item => (
          <div key={item.key} style={{ marginBottom: '10px' }}>
            <label style={{ ...labelStyle, fontSize: '13px' }}>
              <span style={{ color: item.color }}>{item.icon}</span> {item.label}: {formData[item.key]}/10
              <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', marginLeft: '8px' }}>
                {item.desc}
              </span>
            </label>
            <input
              type="range"
              min="0"
              max="10"
              value={formData[item.key]}
              onChange={e => setFormData(prev => ({ ...prev, [item.key]: parseInt(e.target.value) }))}
              style={{ width: '100%', accentColor: item.color }}
            />
          </div>
        ))}
      </div>

      {/* ==================== 多选情绪选择器（87个情绪）==================== */}
      <div style={{ marginBottom: '16px' }}>
        <label style={labelStyle}>🎭 选择你此刻的情绪（可多选）</label>
        <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '10px' }}>
          点击选择多个情绪，系统将综合分析你的情绪状态
        </div>
        
        {/* 已选情绪标签 */}
        {formData.emotions.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '12px' }}>
            {formData.emotions.map((emo, idx) => {
              const emotionDef = emotionTypes.find(e => e.value === emo.type)
              return (
                <span key={idx} style={{
                  padding: '4px 10px',
                  borderRadius: '12px',
                  background: 'rgba(0,122,255,0.2)',
                  border: '1px solid rgba(0,122,255,0.3)',
                  fontSize: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}>
                  {emotionDef?.emoji || '🎭'} {emotionDef?.label || emo.type}
                  <button
                    type="button"
                    onClick={() => removeEmotion(idx)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#ff3b30',
                      cursor: 'pointer',
                      fontSize: '14px',
                      padding: '0 2px',
                    }}
                  >×</button>
                </span>
              )
            })}
          </div>
        )}
        
        {/* 情绪分类折叠面板 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {emotionCategories.map(cat => (
            <details key={cat.key} style={{
              background: 'rgba(255,255,255,0.03)',
              borderRadius: '10px',
              border: '1px solid rgba(255,255,255,0.08)',
            }}>
              <summary style={{
                padding: '10px 14px',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: 500,
                color: 'rgba(255,255,255,0.9)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                listStyle: 'none',
              }}>
                <span style={{ transform: 'rotate(-90deg)', fontSize: '10px' }}>▼</span>
                {cat.label} ({cat.emotions.length}个)
              </summary>
              <div style={{
                padding: '10px 14px',
                display: 'flex',
                flexWrap: 'wrap',
                gap: '6px',
                borderTop: '1px solid rgba(255,255,255,0.05)',
              }}>
                {cat.emotions.map(emo => {
                  const isSelected = formData.emotions.some(e => e.type === emo.value)
                  return (
                    <button
                      key={emo.value}
                      type="button"
                      onClick={() => {
                        if (isSelected) {
                          setFormData(prev => ({
                            ...prev,
                            emotions: prev.emotions.filter(e => e.type !== emo.value)
                          }))
                        } else {
                          setFormData(prev => ({
                            ...prev,
                            emotions: [...prev.emotions, { type: emo.value, intensity: 5, trigger: '' }]
                          }))
                        }
                      }}
                      style={{
                        padding: '6px 10px',
                        borderRadius: '16px',
                        border: isSelected ? '1px solid #007aff' : '1px solid rgba(255,255,255,0.15)',
                        background: isSelected ? 'rgba(0,122,255,0.25)' : 'rgba(255,255,255,0.05)',
                        color: isSelected ? '#fff' : 'rgba(255,255,255,0.7)',
                        fontSize: '12px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        transition: 'all 0.2s',
                      }}
                    >
                      <span>{emo.emoji}</span>
                      <span>{emo.label}</span>
                    </button>
                  )
                })}
              </div>
            </details>
          ))}
        </div>
      </div>

      {/* 内心状态描述 — 灵镜分析输入 */}
      <div style={{ marginBottom: '16px' }}>
        <label style={labelStyle}>描述此刻的内心状态 *</label>
        <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.45)', marginBottom: '10px', lineHeight: 1.6 }}>
          描述此刻的内心状态、正在思考的事情、或面临的选择。<br/>
          系统将自动提取情绪、注意力、决策驱动，并进行内在智慧辨识。
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
          {QUICK_PROMPTS.map((q, i) => (
            <button
              key={i}
              type="button"
              onClick={() => {
                setFormData(prev => ({ ...prev, description: q.t }))
                handleMvfeAnalysis(q.t)
              }}
              style={{
                padding: '6px 12px',
                borderRadius: '20px',
                border: '1px solid rgba(255,255,255,0.08)',
                background: 'rgba(255,255,255,0.03)',
                color: 'rgba(255,255,255,0.7)',
                fontSize: '12px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span>{q.e}</span>
              <span>{q.l}</span>
            </button>
          ))}
        </div>
        <textarea
          value={formData.description}
          onChange={e => setFormData(prev => ({ ...prev, description: e.target.value }))}
          placeholder="或者，在这里自由写下你的感受..."
          style={{ ...inputStyle, minHeight: '100px', resize: 'vertical', lineHeight: 1.7 }}
          required
        />

        {/* 灵镜分析按钮 */}
        <button
          type="button"
          onClick={() => handleMvfeAnalysis()}
          disabled={mvfeProcessing || !formData.description.trim()}
          style={{
            width: '100%',
            marginTop: '10px',
            padding: '12px',
            borderRadius: '12px',
            border: 'none',
            background: mvfeProcessing ? 'rgba(79,172,254,0.15)' : 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
            color: '#fff',
            fontSize: '14px',
            fontWeight: 700,
            cursor: mvfeProcessing ? 'wait' : 'pointer',
            transition: 'all 0.3s',
          }}
        >
          {mvfeProcessing ? '⏳ 灵镜分析中...' : '🔬 灵镜分析'}
        </button>
        {mvfeError && <div style={{ marginTop: '8px', padding: '8px 12px', borderRadius: '8px', background: 'rgba(255,50,50,0.06)', color: '#ff6b6b', fontSize: '12px', borderLeft: '3px solid #ff6b6b' }}>{mvfeError}</div>}

        {/* 灵镜分析结果摘要 */}
        {mvfeResult && (
          <div style={{
            marginTop: '12px',
            padding: '12px',
            borderRadius: '10px',
            background: 'rgba(79,172,254,0.06)',
            border: '1px solid rgba(79,172,254,0.15)',
          }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#4facfe', marginBottom: '8px' }}>✅ 灵镜分析完成 — 已自动填充状态快照</div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', fontSize: '11px' }}>
              {mvfeResult.emotion?.primary_emotion && (
                <span style={{ padding: '3px 8px', borderRadius: '10px', background: 'rgba(255,169,77,0.12)', color: '#ffa94d' }}>
                  🎭 {mvfeResult.emotion.primary_emotion} ({Math.round((mvfeResult.emotion.intensity||0)*100)}%)
                </span>
              )}
              {mvfeResult.attention?.focus && (
                <span style={{ padding: '3px 8px', borderRadius: '10px', background: 'rgba(79,172,254,0.12)', color: '#4facfe' }}>
                  👁 {mvfeResult.attention.focus}
                </span>
              )}
              {mvfeResult.decision?.type && (
                <span style={{ padding: '3px 8px', borderRadius: '10px', background: mvfeResult.decision.type === 'approach' ? 'rgba(81,207,102,0.12)' : 'rgba(255,107,107,0.12)', color: mvfeResult.decision.type === 'approach' ? '#51cf66' : '#ff6b6b' }}>
                  ⚖️ {mvfeResult.decision.type === 'approach' ? '趋近' : '回避'}
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 提示信息 — 说明灵镜分析已包含内在辨识 */}
      <div style={{
        padding: '12px 16px',
        borderRadius: '10px',
        background: 'rgba(79,172,254,0.08)',
        border: '1px solid rgba(79,172,254,0.2)',
        fontSize: '12px',
        color: 'rgba(255,255,255,0.6)',
        textAlign: 'center',
        lineHeight: 1.6,
      }}>
        💡 点击上方「灵镜分析」按钮，系统将同时进行情绪分析并自动启动内在智慧辨识（需填写标题和类别）
      </div>
    </form>
    </>
  )

  // 渲染分析结果
  const renderAnalysisResult = () => {
    if (!analysisResult) return null
    
    const { motive_analysis, discernment_result, guidance } = analysisResult
    
    return (
      <div style={{ padding: '16px' }}>
        <div style={{
          background: 'rgba(0,122,255,0.1)',
          borderRadius: '12px',
          padding: '16px',
          marginBottom: '16px',
        }}>
          <div style={{ fontSize: '16px', fontWeight: 600, color: '#007aff', marginBottom: '12px' }}>
            🎯 分析结果
          </div>
          
          {/* 动机分析 */}
          {motive_analysis && (
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '13px', fontWeight: 500, marginBottom: '8px', color: '#fff' }}>
                📊 动机分析
              </div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {[
                  { label: '恐惧驱动', score: motive_analysis.fear_driven_score, color: '#ff6b6b' },
                  { label: '骄傲驱动', score: motive_analysis.pride_driven_score, color: '#ffa94d' },
                  { label: '爱驱动', score: motive_analysis.love_driven_score, color: '#51cf66' },
                  { label: '欲望驱动', score: motive_analysis.desire_driven_score, color: '#9775fa' },
                ].map(item => (
                  <div key={item.label} style={{
                    padding: '6px 12px',
                    borderRadius: '8px',
                    background: `${item.color}20`,
                    border: `1px solid ${item.color}40`,
                  }}>
                    <span style={{ fontSize: '11px', color: item.color }}>{item.label}</span>
                    <span style={{ fontSize: '14px', fontWeight: 600, color: item.color, marginLeft: '6px' }}>
                      {Math.round(item.score * 100)}%
                    </span>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: '8px', fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>
                主导动机: <span style={{ color: '#fff', fontWeight: 500 }}>{motive_analysis.dominant_motive}</span>
              </div>
            </div>
          )}
          
          {/* 辨识结果 */}
          {discernment_result && (
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '13px', fontWeight: 500, marginBottom: '8px', color: '#fff' }}>
                🔮 内在智慧辨识
              </div>
              <div style={{
                padding: '12px',
                borderRadius: '10px',
                background: 'rgba(255,255,255,0.05)',
                fontSize: '13px',
                lineHeight: 1.6,
                color: 'rgba(255,255,255,0.8)',
              }}>
                <div style={{ marginBottom: '8px' }}>
                  <span style={{ color: '#4facfe', fontWeight: 500 }}>主要来源:</span> {discernment_result.primary_source}
                </div>
                <div style={{ marginBottom: '8px' }}>
                  <span style={{ color: '#4facfe', fontWeight: 500 }}>置信度:</span> {Math.round(discernment_result.confidence * 100)}%
                </div>
                <div>{discernment_result.explanation}</div>
              </div>
            </div>
          )}
          
          {/* 指导建议 */}
          {guidance && (
            <div>
              <div style={{ fontSize: '13px', fontWeight: 500, marginBottom: '8px', color: '#fff' }}>
                💡 指导建议
              </div>
              <div style={{
                padding: '12px',
                borderRadius: '10px',
                background: 'rgba(255,255,255,0.05)',
                fontSize: '13px',
                lineHeight: 1.6,
                color: 'rgba(255,255,255,0.8)',
              }}>
                <div style={{ marginBottom: '12px' }}>{guidance.structured_advice}</div>
                
                {guidance.risks?.length > 0 && (
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 500, color: '#ff6b6b', marginBottom: '4px' }}>
                      ⚠️ 潜在风险
                    </div>
                    <ul style={{ margin: 0, paddingLeft: '16px' }}>
                      {guidance.risks.map((risk, i) => (
                        <li key={i} style={{ marginBottom: '2px' }}>{risk}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {guidance.recommended_actions?.length > 0 && (
                  <div>
                    <div style={{ fontSize: '12px', fontWeight: 500, color: '#51cf66', marginBottom: '4px' }}>
                      ✅ 建议行动
                    </div>
                    <ul style={{ margin: 0, paddingLeft: '16px' }}>
                      {guidance.recommended_actions.map((action, i) => (
                        <li key={i} style={{ marginBottom: '2px' }}>{action}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  // 渲染历史记录
  const renderHistory = () => (
    <div style={{ padding: '16px' }}>
      {decisions.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px 20px', color: 'rgba(255,255,255,0.5)' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>📝</div>
          <div style={{ fontSize: '15px' }}>暂无决策记录</div>
          <div style={{ fontSize: '13px', marginTop: '8px' }}>开始记录你的第一个重要决策吧</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {decisions.map(decision => (
            <div
              key={decision.id}
              onClick={() => setSelectedDecision(decision.id === selectedDecision?.id ? null : decision)}
              style={{
                padding: '16px',
                borderRadius: '12px',
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.1)',
                cursor: 'pointer',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '15px', fontWeight: 500, color: '#fff', marginBottom: '4px' }}>
                    {decision.title}
                  </div>
                  <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)' }}>
                    {decisionCategories.find(c => c.value === decision.category)?.label || decision.category} · 
                    {new Date(decision.created_at).toLocaleDateString('zh-CN')}
                  </div>
                </div>
                <div style={{
                  padding: '4px 10px',
                  borderRadius: '12px',
                  fontSize: '12px',
                  background: decision.status === 'guided' ? 'rgba(0,122,255,0.2)' : 'rgba(255,193,7,0.2)',
                  color: decision.status === 'guided' ? '#4facfe' : '#ffc107',
                }}>
                  {decision.status === 'guided' ? '已分析' : '分析中'}
                </div>
              </div>
              
              {selectedDecision?.id === decision.id && decision.motive_analysis && (
                <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                  <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>
                    主导动机: {decision.motive_analysis.dominant_motive}
                  </div>
                  {decision.discernment_result && (
                    <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)', marginTop: '4px' }}>
                      辨识来源: {decision.discernment_result.primary_source}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )

  // 渲染原则列表
  const renderPrinciples = () => (
    <div style={{ padding: '16px' }}>
      <div style={{ fontSize: '14px', fontWeight: 500, color: '#fff', marginBottom: '16px' }}>
        📖 内在智慧原则
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {wisdomPrinciples.map((principle, i) => (
          <div
            key={principle.id}
            style={{
              padding: '14px',
              borderRadius: '10px',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.1)',
            }}
          >
            <div style={{ fontSize: '14px', color: '#fff', lineHeight: 1.5 }}>
              {principle.text}
            </div>
            <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '6px' }}>
              {principle.ref}
            </div>
          </div>
        ))}
      </div>
    </div>
  )

  // 样式定义
  const labelStyle = {
    display: 'block',
    fontSize: '14px',
    fontWeight: 500,
    color: '#fff',
    marginBottom: '6px',
  }

  const inputStyle = {
    width: '100%',
    padding: '12px',
    borderRadius: '10px',
    border: '1px solid rgba(255,255,255,0.2)',
    background: 'rgba(255,255,255,0.05)',
    color: '#fff',
    fontSize: '14px',
    outline: 'none',
  }

  // 提交按钮
  const renderSubmitButton = () => (
    <div style={{ padding: '16px', paddingTop: 0 }}>
      <button
        type="submit"
        form="decision-form"
        disabled={loading || !formData.title || !formData.category || !formData.description}
        style={{
          width: '100%',
          padding: '14px',
          borderRadius: '12px',
          border: 'none',
          background: loading ? 'rgba(0,122,255,0.5)' : '#007aff',
          color: '#fff',
          fontSize: '15px',
          fontWeight: 600,
          cursor: loading ? 'wait' : 'pointer',
          opacity: (!formData.title || !formData.category || !formData.description) ? 0.5 : 1,
        }}
      >
        {loading ? '⏳ 提交分析中...' : '✨ 提交决策分析'}
      </button>
    </div>
  )

  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: '#1c1c1e',
      color: '#fff',
      overflow: 'hidden',
    }}>
      {/* 头部导航 */}
      {renderTabs()}
      
      {/* 用户标签 */}
      {renderUserTags()}
      
      {/* 内容区域 */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {activeTab === 'new' && (
          <>
            {analysisResult ? renderAnalysisResult() : renderNewDecisionForm()}
            {activeTab === 'new' && !analysisResult && renderSubmitButton()}
          </>
        )}
        {activeTab === 'history' && renderHistory()}
        {activeTab === 'principles' && renderPrinciples()}
      </div>
    </div>
  )
}
