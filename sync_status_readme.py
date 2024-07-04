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
current_date = datetime.now(beijing_tz).date()

def check_md_content(file_content, date):
    try:
        date_patterns = [
            r'###\s*' + date.strftime("%Y.%m.%d"),
            r'###\s*' + date.strftime("%Y.%-m.%-d"),
            r'###\s*' + date.strftime("%-m.%-d")
        ]
        combined_pattern = '|'.join(date_patterns)
        current_date_match = re.search(combined_pattern, file_content)
        if not current_date_match:
            return False
        
        start_pos = current_date_match.end()
        next_date_pattern = r'###\s*(\d{4}\.)?(\d{1,2}\.\d{1,2})'
        next_date_match = re.search(next_date_pattern, file_content[start_pos:])
        
        if next_date_match:
            end_pos = start_pos + next_date_match.start()
            content = file_content[start_pos:end_pos]
        else:
            content = file_content[start_pos:]
        
        content = re.sub(r'\s', '', content)
        return len(content) > 10
    except Exception as e:
        logging.error(f"Error in check_md_content: {str(e)}")
        return False

def get_user_study_status(nickname):
    user_status = {}
    file_name = f"{nickname}_EICL1st.md"
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            file_content = file.read()
        for date in date_range:
            if date.date() > current_date:
                user_status[date] = " "  # 未来的日期显示为空白
            elif date.date() == current_date:
                user_status[date] = "✅" if check_md_content(file_content, date) else " "  # 当天有内容标记✅,否则空白
            else:
                user_status[date] = "✅" if check_md_content(file_content, date) else "⭕️"
        logging.info(f"Successfully processed file for user: {nickname}")
    except FileNotFoundError:
        logging.error(f"Error: Could not find file {file_name}")
        user_status = {date: "⭕️" for date in date_range}
    except Exception as e:
        logging.error(f"Unexpected error processing file for {nickname}: {str(e)}")
        user_status = {date: "⭕️" for date in date_range}
    return user_status

def check_weekly_status(user_status, date):
    try:
        week_start = date.date() - timedelta(days=date.weekday())
        week_dates = [week_start + timedelta(days=x) for x in range(7)]
        week_dates = [d for d in week_dates if d in [date.date() for date in date_range] and d <= date.date()]
        missing_days = sum(1 for d in week_dates if user_status.get(datetime.combine(d, datetime.min.time(), tzinfo=beijing_tz), "⭕️") == "⭕️")
        return "❌" if missing_days > 2 else user_status.get(date, "⭕️")
    except Exception as e:
        logging.error(f"Error in check_weekly_status: {str(e)}")
        return "⭕️"

def update_readme(content, start_marker, end_marker):
    try:
        start_index = content.find(start_marker)
        end_index = content.find(end_marker)
        if start_index == -1 or end_index == -1:
            logging.error("Error: Couldn't find the table markers in README.md")
            return content

        table_content = content[start_index + len(start_marker):end_index].strip()
        table_rows = table_content.split('\n')[2:]  # 跳过表头和分隔行

        new_table = [
            f'{start_marker}\n',
            '| EICL1st· Name | ' + ' | '.join(date.strftime("%-m.%-d") for date in date_range) + ' |\n',
            '| ------------- | ' + ' | '.join(['----' for _ in date_range]) + ' |\n'
        ]

        for row in table_rows:
            match = re.match(r'\|\s*([^|]+)\s*\|', row)
            if match:
                display_name = match.group(1).strip()
                user_status = get_user_study_status(display_name)
                new_row = f"| {display_name} |"
                for date in date_range:
                    status = check_weekly_status(user_status, date)
                    new_row += f" {status} |"
                new_table.append(new_row + '\n')
            else:
                logging.warning(f"Skipping invalid row: {row}")
                new_table.append(row + '\n')

        new_table.append(f'{end_marker}\n')

        return (
            content[:start_index] +
            ''.join(new_table) +
            content[end_index + len(end_marker):]
        )
    except Exception as e:
        logging.error(f"Error in update_readme: {str(e)}")
        return content

def main():
    try:
        with open('README.md', 'r', encoding='utf-8') as file:
            content = file.read()

        new_content = update_readme(content, "<!-- START_COMMIT_TABLE -->", "<!-- END_COMMIT_TABLE -->")

        with open('README.md', 'w', encoding='utf-8') as file:
            file.write(new_content)

        logging.info("README.md has been successfully updated.")
    except Exception as e:
        logging.error(f"An error occurred in main function: {str(e)}")

if __name__ == "__main__":
    main()