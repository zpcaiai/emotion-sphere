import re

REPLACEMENTS = [
    ("被领导当众批评，觉得自己很无能", '{"羞耻","愤怒","挫败"}', 8, '{"scene":"work","trigger":"public_criticism"}'),
    ("凌晨三点还睡不着，反复回想白天的事", '{"焦虑","失眠","反刍"}', 9, '{"scene":"bedtime","trigger":"rumination"}'),
    ("和朋友吵架后，觉得自己不被爱", '{"悲伤","孤独","被抛弃感"}', 7, '{"scene":"friendship","trigger":"conflict"}'),
    ("考试前手心冒汗，脑子里一片空白", '{"恐惧","紧张","无助"}', 8, '{"scene":"exam","trigger":"performance_pressure"}'),
    ("看到社交媒体上别人的完美生活，感到自卑", '{"嫉妒","自卑","孤独"}', 6, '{"scene":"social_media","trigger":"comparison"}'),
    ("终于完成了拖延两周的报告，如释重负", '{"轻松","成就感","解脱"}', 3, '{"scene":"work","trigger":"task_completion"}'),
    ("独自走在雨中，突然感到莫名的平静", '{"平静","感恩","孤独中的平安"}', 4, '{"scene":"nature","trigger":"rain_walk"}'),
    ("被父母催婚，感到巨大的压力和愧疚", '{"焦虑","愧疚","愤怒"}', 8, '{"scene":"family","trigger":"marriage_pressure"}'),
    ("跑步五公里后，心情舒畅很多", '{"放松","成就感","活力"}', 3, '{"scene":"exercise","trigger":"endorphin_release"}'),
    ("在教会敬拜中流泪，感到被神拥抱", '{"感恩","被爱","释放"}', 4, '{"scene":"worship","trigger":"spiritual_connection"}'),
    ("工作中被同事抢功劳，气得发抖", '{"愤怒","不公","背叛"}', 9, '{"scene":"work","trigger":"unfair_treatment"}'),
    ("失业三个月后终于拿到offer，感恩主", '{"喜乐","感恩","希望"}', 2, '{"scene":"career","trigger":"job_offer"}'),
    ("和室友冷战一周，家里气氛压抑", '{"疲惫","愤怒","回避"}', 7, '{"scene":"home","trigger":"roommate_conflict"}'),
    ("祷告一小时后内心得平安，不再焦虑", '{"平安","感恩","信心"}', 3, '{"scene":"prayer","trigger":"spiritual_practice"}'),
    ("又一次刷手机到半夜，痛恨自己的自制力", '{"自责","挫败","空虚"}', 8, '{"scene":"bedtime","trigger":"phone_addiction"}'),
]

with open('/Users/stephen/Documents/python/emotion-sphere/backend/seed_all.sql', 'r') as f:
    lines = f.readlines()

new_lines = []
idx = 0
for line in lines:
    if 'INSERT INTO emotion_logs' in line and idx < len(REPLACEMENTS):
        text, tags, intensity, ctx = REPLACEMENTS[idx]
        m = re.search(r"'([0-9a-f-]+)'", line)
        uid = m.group(1) if m else 'uuid'
        m2 = re.search(r"'[0-9a-f-]+', (\d+),", line)
        user_id = m2.group(1) if m2 else str((idx % 5) + 1)
        new_line = f"INSERT INTO emotion_logs (id, user_id, raw_text, emotion_tags, intensity, occurred_at, context_json, source) VALUES ('{uid}', {user_id}, '{text}', '{tags}', {intensity}, '2025-03-{(idx+1):02d} 18:00:00', '{ctx}', 'web');\n"
        new_lines.append(new_line)
        idx += 1
    else:
        new_lines.append(line)

with open('/Users/stephen/Documents/python/emotion-sphere/backend/seed_all.sql', 'w') as f:
    f.writelines(new_lines)

print(f'Replaced {idx} emotion_logs rows')
