import os
import re
from github import Github
from datetime import datetime, timedelta
import pytz

# 初始化GitHub API
g = Github(os.environ['GITHUB_TOKEN'])
repo = g.get_repo(os.environ['GITHUB_REPOSITORY'])

# 设置北京时区
beijing_tz = pytz.timezone('Asia/Shanghai')

# 定义日期范围（从6月24日到7月14日）
start_date = datetime(2024, 6, 24, tzinfo=beijing_tz)
end_date = datetime(2024, 7, 14, tzinfo=beijing_tz)
date_range = [(start_date + timedelta(days=x)).strftime("%m.%d") for x in range((end_date - start_date).days + 1)]

# 获取当前北京时间
current_date = datetime.now(beijing_tz)

def check_md_content(file_content, date):
    date_pattern = r'###\s*' + date.replace('.', r'\.')
    content_pattern = date_pattern + r'([\s\S]*?)(?=###|\Z)'
    match = re.search(content_pattern, file_content)
    if match:
        content = match.group(1).strip()
        return len(content) > 10
    return False

# 获取每个用户在每一天的学习状态
def get_user_study_status(nickname):
    user_status = {}
    file_name = f"{nickname}_EICL1st.md"
    try:
        file_content = repo.get_contents(file_name).decoded_content.decode('utf-8')
        for date in date_range:
            day = datetime.strptime(date, "%m.%d").replace(year=2024, tzinfo=beijing_tz)
            if day > current_date:
                user_status[date] = " "  # 未来的日期显示为空白
            else:
                user_status[date] = "✅" if check_md_content(file_content, date) else "⭕️"
    except:
        for date in date_range:
            user_status[date] = "⭕️"
    return user_status

# 检查是否有人在一周内超过两天没有提交
def check_weekly_status(user_status, date):
    week_start = datetime.strptime(date, "%m.%d").replace(year=2024, tzinfo=beijing_tz)
    week_start -= timedelta(days=week_start.weekday())  # 调整到本周一
    week_dates = [(week_start + timedelta(days=x)).strftime("%m.%d") for x in range(7)]
    week_dates = [d for d in week_dates if d in date_range and d <= date]
    
    missing_days = sum(1 for d in week_dates if user_status.get(d, "⭕️") == "⭕️")
    return "❌" if missing_days > 2 else user_status.get(date, "⭕️")

# 读取README.md文件
with open('README.md', 'r') as file:
    content = file.read()

# 查找标记并提取表格内容
start_marker = "<!-- START_COMMIT_TABLE -->"
end_marker = "<!-- END_COMMIT_TABLE -->"
start_index = content.find(start_marker)
end_index = content.find(end_marker)

if start_index != -1 and end_index != -1:
    table_content = content[start_index + len(start_marker):end_index].strip()
    table_rows = table_content.split('\n')[2:]  # 跳过表头和分隔行
    
    # 解析现有表格并更新学习状态
    new_table = ['| EICL1st· Name | ' + ' | '.join(date_range) + ' |\n',
                 '| ------------- | ' + ' | '.join(['----' for _ in date_range]) + ' |\n']
    
    for row in table_rows:
        match = re.match(r'\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|', row)
        if match:
            display_name = match.group(1)
            github_url = match.group(2)
            
            user_status = get_user_study_status(display_name)
            new_row = f"| [{display_name}]({github_url}) |"
            for date in date_range:
                status = check_weekly_status(user_status, date)
                new_row += f" {status} |"
            new_table.append(new_row + '\n')
        else:
            new_table.append(row + '\n')
    
    # 更新README.md文件
    new_content = (
        content[:start_index + len(start_marker)] + 
        '\n' + ''.join(new_table) + '\n' + 
        content[end_index:]
    )
    
    with open('README.md', 'w') as file:
        file.write(new_content)
else:
    print("Error: Couldn't find the table markers in README.md")
