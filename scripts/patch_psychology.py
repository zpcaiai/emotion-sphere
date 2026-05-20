import re

with open('/Users/stephen/Documents/python/emotion-sphere/backend/seed_all.sql', 'r') as f:
    content = f.read()

# --- personality_drivers ---
problems = ["被领导批评后陷入自我否定","deadline临近时的灾难化思维","人际冲突后的讨好反应","社交媒体比较引发的自卑","考试前的表现焦虑","完成任务后的空虚感","独处时的无价值感","家庭压力下的情绪崩溃"]
deeps = ["羞耻感","恐惧感","被抛弃恐惧","低自尊","完美主义焦虑","存在性空虚","孤独感","愧疚感"]
hiddens = ["完美主义驱动的自我价值绑定","灾难化思维模式","讨好型人格的边界模糊","社会比较的自我定义","成就导向的身份认同","外在认可的内在空洞","回避型依恋的激活","家庭角色期望的冲突"]
beliefs = ["If I fail, I am worthless","I cannot handle pressure","If someone is upset, it is my fault","Others are better than me","I must be perfect to be accepted","My worth depends on productivity","I am fundamentally alone","I must meet everyone's expectations"]
for i in range(8):
    content = content.replace(f"'problem{i}'", f"'{problems[i]}'")
    content = content.replace(f"'deep{i}'", f"'{deeps[i]}'")
    content = content.replace(f"'hidden{i}'", f"'{hiddens[i]}'")
    content = content.replace(f"'belief{i}'", f"'{beliefs[i]}'")

# --- behavioral_triggers ---
tnames = ["deadline_approaching","social_media_comparison","public_criticism","family_conflict","exam_pressure","loneliness_evening"]
tpats = ["距截止72小时内","打开朋友圈看到成功案例","会议中被点名指出错误","节假日家庭聚餐","考前一周复习","晚上10点后独自在家"]
events = ["看到截止日期日历提醒","无意识滑动手机屏幕","领导点名发言","父母开始询问婚姻状况","翻开课本发现还有很多没看","室友们都已入睡"]
for i in range(6):
    content = content.replace(f"'trigger{i}'", f"'{tnames[i]}'")
    content = content.replace(f"'pattern{i}'", f"'{tpats[i]}'")
    content = content.replace(f"'event{i}'", f"'{events[i]}'")

# --- cognitive_schemas ---
schemas = ["我不够好","我不可爱","我必须完美","我无能","我会被拒绝","我不值得","我危险","我失控"]
sbeliefs = ["If I make a mistake, I am a failure","If people really knew me, they would leave","I must do everything flawlessly or I am worthless","I am incapable of handling life's challenges","I will inevitably be abandoned by those I love","I don't deserve good things","The world is dangerous and I am vulnerable","I have no control over my emotions or life"]
for i in range(8):
    content = content.replace(f"'schema{i}'", f"'{schemas[i]}'")
    content = content.replace(f"'belief{i}'", f"'{sbeliefs[i]}'")

# --- behavioral_experiments ---
exptitles = ["故意不完美提交报告","主动表达不同意见","在陌生人面前犯错","请求帮助而非独自承担","公开分享失败经历","减少社交媒体使用"]
exphyps = ["如果不反复检查，结果也不会灾难性","表达不同意见不会导致关系破裂","即使出丑，他人也不会过度关注","请求帮助不会显得无能","分享失败会拉近人与人距离","减少比较会提升自我价值感"]
for i in range(6):
    content = content.replace(f"'experiment {i}'", f"'{exptitles[i]}'")
    content = content.replace(f"'hypothesis{i}'", f"'{exphyps[i]}'")

# --- psychological_states ---
stnames = ["regulated","mild_dysregulation","moderate_dysregulation","severe_dysregulation","recovery","regulated","mild_dysregulation","regulated","regulated","moderate_dysregulation"]
actions = ["维持当前活动","5-4-3-2-1 grounding","暂停任务，深呼吸","启动安全基地协议","渐进式重启","维持当前活动","短暂休息","维持当前活动","维持当前活动","任务降级"]
for i in range(10):
    content = content.replace(f"'regulated', {(i%5)},", f"'{stnames[i]}', {(i%5)},", 1)
    content = content.replace("'breathe'", f"'{actions[i]}'", 1)

# --- intervention_logs ---
prompts = ["现在注意到脚下的地面","轻轻把手放在胸口","深呼吸三次","告诉自己：这是焦虑，不是危险","慢慢数五个周围的颜色","站起来伸展身体","喝一杯温水","写下一个你感激的小事"]
techs = ["grounding","self_soothing","breathing","cognitive_labeling","sensory_anchoring","movement","somatic_regulation","gratitude_priming"]
for i in range(8):
    content = content.replace(f"'prompt{i}'", f"'{prompts[i]}'")
    content = content.replace(f"'grounding'", f"'{techs[i]}'", 1)

# --- identity_narratives ---
ititles = ["从完美主义到真实自我","从取悦他人到设立边界","从逃避到面对","从受害者到幸存者","从比较到感恩","从控制到交托"]
itexts = ["我一直追求完美，直到发现完美让我窒息。","我学会了说'不'，这反而让我更受欢迎。","每次逃避都让我更害怕，现在选择面对。","我不再问'为什么是我'，而是问'这教会了我什么'。","当我停止比较，才发现自己已经很富足。","放下控制的手，我才真正摸到自由。"]
for i in range(6):
    content = content.replace(f"'title{i}'", f"'{ititles[i]}'")
    content = content.replace(f"'text{i}'", f"'{itexts[i]}'")

# --- pattern_recognitions ---
pnames = ["睡前情绪崩溃","社交回避循环","拖延-焦虑螺旋","完美主义瘫痪","愤怒-内疚循环"]
pdescs = ["晚上10点后情绪显著低落，伴随反刍思维","面对邀请先答应后找理由取消","任务截止前24小时焦虑激增但仍无法启动","准备阶段过度打磨导致无法交付","被冒犯后愤怒爆发，随后深度自责"]
for i in range(5):
    content = content.replace(f"'pattern{i}'", f"'{pnames[i]}'")
    content = content.replace(f"'desc{i}'", f"'{pdescs[i]}'")

# --- memory_consolidations ---
mtitles = ["高考失利","第一次祷告流泪","被好友背叛","面试成功","父亲生病住院","独自海外求学"]
mcontents = ["高考前夜失眠，考场上头脑空白，成绩远低于预期。","在教会敬拜中突然泪流满面，感到前所未有的平安。","发现最好的朋友在背后说我的坏话，信任崩塌。","经历了三个月失业后，终于拿到心仪的offer。","接到母亲电话说父亲中风，连夜赶回老家。","18岁第一次一个人飞出国，既害怕又兴奋。"]
for i in range(6):
    content = content.replace(f"'memory{i}'", f"'{mtitles[i]}'")
    content = content.replace(f"'content{i}'", f"'{mcontents[i]}'")

# --- behavior_regulation_sessions ---
hbits = ["晨祷","运动","阅读","写日记","早睡","专注工作","社交","灵修"]
for i in range(8):
    content = content.replace(f"'habit{i}'", f"'{hbits[i]}'")

# --- habit_state_machines ---
hnames = ["每日晨祷","每周运动3次","睡前阅读30分钟","情绪日记","23点前睡觉","深度工作时段"]
hdescs = ["起床后15分钟安静灵修","跑步/游泳/骑行","非虚构类书籍","记录当日情绪与触发器","放下手机准备入睡","上午2小时无干扰专注时间"]
hanchors = ["闹钟响起后","周一/三/五下班","洗漱完毕上床","晚餐后","21:30手机充电","到达办公室后"]
for i in range(6):
    content = content.replace(f"'habit{i}'", f"'{hnames[i]}'")
    content = content.replace(f"'desc{i}'", f"'{hdescs[i]}'")
    content = content.replace(f"'anchor{i}'", f"'{hanchors[i]}'")

# --- execution_paralysis_logs ---
tasks = ["撰写Q1季度报告","准备客户演示PPT","回复积压邮件","开始学习新技能","整理税务文件","写求职信","更新简历","清理衣柜"]
for i in range(8):
    content = content.replace(f"'task{i}'", f"'{tasks[i]}'")

# --- micro_scheduler_sessions ---
btasks = ["撰写Q1季度报告","准备客户演示PPT","回复积压邮件","开始学习新技能","整理税务文件","写求职信"]
for i in range(6):
    content = content.replace(f"'big task {i}'", f"'{btasks[i]}'")

# --- implementation_intentions ---
intnames = ["晨祷习惯","运动启动","阅读仪式","情绪记录","早睡准备","深度工作"]
ifs = ["闹钟响起","下班到家","洗漱完毕","感到情绪波动","21:30","到达办公室"]
thens = ["立即跪祷15分钟","换运动装备出门","拿书上床阅读","打开手机日记APP","手机放到客厅充电","开启勿扰模式"]
for i in range(6):
    content = content.replace(f"'intention{i}'", f"'{intnames[i]}'")
    content = content.replace(f"'if {i}'", f"'{ifs[i]}'")
    content = content.replace(f"'then {i}'", f"'{thens[i]}'")

# --- identity_reinforcement_logs ---
inarratives = ["I am learning to be gentle with myself","I am becoming someone who shows up","I am growing through discomfort","I am choosing courage over comfort","I am enough as I am","I am a work in progress","I am learning to receive love","I am becoming resilient"]
for i in range(8):
    content = content.replace(f"'I am growing'", f"'{inarratives[i]}'", 1)

# --- personality_migrations ---
starts = ["I am fragile","I am a victim","I am unlovable","I am a failure","I am alone"]
targets = ["I am resilient","I am empowered","I am worthy of love","I am learning","I am connected"]
for i in range(5):
    content = content.replace(f"'I am fragile'", f"'{starts[i]}'", 1)
    content = content.replace(f"'I am strong'", f"'{targets[i]}'", 1)

# --- state_transition_logs ---
trigs = ["能量低于阈值","检测到焦虑峰值","完成一次成功干预","社交冲突后","晨间祷告","遭遇批评","运动结束","睡前 rumination","收到好消息","任务完成"]
for i in range(10):
    content = content.replace(f"'trigger{i}'", f"'{trigs[i]}'")

with open('/Users/stephen/Documents/python/emotion-sphere/backend/seed_all.sql', 'w') as f:
    f.write(content)

print("Psychology data patched successfully")
