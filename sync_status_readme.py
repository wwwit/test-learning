import os
import re
from datetime import datetime, timedelta
import pytz
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 设置北京时区
beijing_tz = pytz.timezone('Asia/Shanghai')

# 定义日期范围（从6月24日到7月14日）
start_date = datetime(2024, 6, 24, tzinfo=beijing_tz)
end_date = datetime(2024, 7, 14, tzinfo=beijing_tz)
date_range = [(start_date + timedelta(days=x)) for x in range((end_date - start_date).days + 1)]

# 获取当前北京时间
current_date = datetime.now(beijing_tz)

logging.info(f"脚本开始执行。当前日期: {current_date}")

def check_md_content(file_content, date):
    logging.info(f"检查日期 {date} 的内容")
    # 提取 <!-- EICL1st_START --> 和 <!-- EICL1st_END --> 之间的内容
    start_tag = "<!-- EICL1st_START -->"
    end_tag = "<!-- EICL1st_END -->"
    start_index = file_content.find(start_tag)
    end_index = file_content.find(end_tag)
    
    if start_index != -1 and end_index != -1:
        content = file_content[start_index + len(start_tag):end_index].strip()
        logging.info("找到 EICL1st 标记")
    else:
        content = file_content
        logging.info("未找到 EICL1st 标记，使用整个文件内容")

    date_pattern = r'###\s*' + date.strftime("%Y.%m.%d")
    content_pattern = date_pattern + r'([\s\S]*?)(?=###|\Z)'
    match = re.search(content_pattern, content)
    if match:
        content = match.group(1).strip()
        logging.info(f"找到日期 {date} 的内容，长度: {len(content)}")
        return len(content) > 10
    logging.info(f"未找到日期 {date} 的内容")
    return False

def get_user_study_status(nickname):
    logging.info(f"获取用户 {nickname} 的学习状态")
    user_status = {}
    file_name = f"{nickname}_EICL1st.md"
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            file_content = file.read()
            logging.info(f"成功读取文件 {file_name}")
            for date in date_range:
                if date > current_date:
                    user_status[date] = " "
                    logging.info(f"日期 {date} 是未来日期，标记为空白")
                else:
                    user_status[date] = "✅" if check_md_content(file_content, date) else "⭕️"
                    logging.info(f"日期 {date} 的学习状态: {user_status[date]}")
    except FileNotFoundError:
        logging.error(f"错误: 找不到文件 {file_name}")
        for date in date_range:
            user_status[date] = "⭕️"
    return user_status

def check_weekly_status(user_status, date):
    logging.info(f"检查 {date} 的每周状态")
    week_start = date - timedelta(days=date.weekday())
    week_dates = [week_start + timedelta(days=x) for x in range(7)]
    week_dates = [d for d in week_dates if d in date_range and d <= date]
    missing_days = sum(1 for d in week_dates if user_status.get(d, "⭕️") == "⭕️")
    status = "❌" if missing_days > 2 else user_status.get(date, "⭕️")
    logging.info(f"每周状态: {status}，缺失天数: {missing_days}")
    return status

# 读取README.md文件
logging.info("开始读取 README.md 文件")
with open('README.md', 'r', encoding='utf-8') as file:
    content = file.read()
logging.info("成功读取 README.md 文件")

# 查找标记并提取表格内容
start_marker = "<!-- START_COMMIT_TABLE -->"
end_marker = "<!-- END_COMMIT_TABLE -->"

start_index = content.find(start_marker)
end_index = content.find(end_marker)

logging.info(f"查找表格标记。开始标记索引: {start_index}, 结束标记索引: {end_index}")

if start_index != -1 and end_index != -1:
    table_content = content[start_index + len(start_marker):end_index].strip()
    table_rows = table_content.split('\n')[2:]  # 跳过表头和分隔行
    logging.info(f"成功提取表格内容。行数: {len(table_rows)}")

    # 解析现有表格并更新学习状态
    # new_table = [
    #     '| EICL1st· Name | ' + ' | '.join(date.strftime("%-m.%-d") for date in date_range) + ' |\n',
    #     '| ------------- | ' + ' | '.join(['----' for _ in date_range]) + ' |\n'
    # ]
    new_table = ['| EICL1st· Name | ' + ' | '.join(date_range) + ' |\n',
             '| ------------- | ' + ' | '.join(['----' for _ in date_range]) + ' |\n']

    for row in table_rows:
        match = re.match(r'\|\s*\[([^\]]+)\]', row)
        if match:
            display_name = match.group(1)
            logging.info(f"处理用户: {display_name}")
            user_status = get_user_study_status(display_name)
            new_row = f"| [{display_name}]" + row[row.index(']'):row.index('|', 1)] + "|"
            for date in date_range:
                status = check_weekly_status(user_status, date)
                new_row += f" {status} |"
            new_table.append(new_row + '\n')
            logging.info(f"更新了 {display_name} 的状态")
        else:
            new_table.append(row + '\n')
            logging.info("添加了一行不包含用户名的行")

    # 更新README.md文件
    new_content = (
        content[:start_index] +
        start_marker + '\n' +
        ''.join(new_table) +
        end_marker +
        content[end_index + len(end_marker):]
    )

    logging.info("准备写入更新后的 README.md 文件")
    with open('README.md', 'w', encoding='utf-8') as file:
        file.write(new_content)
    logging.info("成功更新 README.md 文件")
else:
    logging.error("错误: 在 README.md 中找不到表格标记")

logging.info("脚本执行完毕")
