import os
import re
from datetime import datetime, timedelta
import pytz
import logging

# 设置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# 设置UTC时区
utc_tz = pytz.UTC

# 定义日期范围（从6月24日到7月14日）
start_date = datetime(2024, 6, 24, 16, 0, tzinfo=utc_tz)
end_date = datetime(2024, 7, 14, 16, 0, tzinfo=utc_tz)
date_range = [(start_date + timedelta(days=x))
              for x in range((end_date - start_date).days + 1)]

# 获取当前UTC时间
current_date = datetime.now(utc_tz)


def get_submission_date(timestamp):
    # 将时间戳转换为 UTC
    utc_time = timestamp.astimezone(utc_tz)

    # 计算提交日期
    submission_date = utc_time.date()
    if utc_time.hour < 16:
        submission_date -= timedelta(days=1)

    return submission_date


def check_md_content(file_content, date):
    try:
        # 查找标记之间的内容
        start_marker = "<!-- EICL1st_START -->"
        end_marker = "<!-- EICL1st_END -->"
        start_index = file_content.find(start_marker)
        end_index = file_content.find(end_marker)

        if start_index == -1 or end_index == -1:
            logging.warning("EICL1st markers not found in the file")
            return False

        # 提取标记之间的内容
        content = file_content[start_index +
                               len(start_marker):end_index].strip()

        # 在提取的内容中查找日期
        date_patterns = [
            r'###\s*' + date.strftime("%Y.%m.%d"),
            r'###\s*' + date.strftime("%Y.%-m.%-d"),
            r'###\s*' + date.strftime("%-m.%-d")
        ]
        combined_pattern = '|'.join(date_patterns)
        current_date_match = re.search(combined_pattern, content)

        if not current_date_match:
            return False

        start_pos = current_date_match.end()
        next_date_pattern = r'###\s*(\d{4}\.)?(\d{1,2}\.\d{1,2})'
        next_date_match = re.search(next_date_pattern, content[start_pos:])

        if next_date_match:
            end_pos = start_pos + next_date_match.start()
            date_content = content[start_pos:end_pos]
        else:
            date_content = content[start_pos:]

        date_content = re.sub(r'\s', '', date_content)
        return len(date_content) > 10
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
            submission_date = get_submission_date(current_date)
            if date.date() > submission_date:
                user_status[date] = " "  # 未来的日期显示为空白
            elif date.date() == submission_date:
                user_status[date] = "✅" if check_md_content(
                    file_content, date) else " "  # 当天有内容标记✅,否则空白
            else:
                user_status[date] = "✅" if check_md_content(
                    file_content, date) else "⭕️"
        logging.info(f"Successfully processed file for user: {nickname}")
    except FileNotFoundError:
        logging.error(f"Error: Could not find file {file_name}")
        user_status = {date: "⭕️" for date in date_range}
    except Exception as e:
        logging.error(
            f"Unexpected error processing file for {nickname}: {str(e)}")
        user_status = {date: "⭕️" for date in date_range}
    return user_status


def check_weekly_status(user_status, date):
    try:
        week_start = date.date() - timedelta(days=date.weekday())
        week_dates = [week_start + timedelta(days=x) for x in range(7)]
        week_dates = [d for d in week_dates if d in [date.date()
                                                     for date in date_range] and d <= get_submission_date(current_date)]
        missing_days = sum(1 for d in week_dates if user_status.get(
            datetime.combine(d, datetime.min.time(), tzinfo=utc_tz), "⭕️") == "⭕️")
        return "❌" if missing_days > 2 else user_status.get(date, "⭕️")
    except Exception as e:
        logging.error(f"Error in check_weekly_status: {str(e)}")
        return "⭕️"


def get_all_user_files():
    return [f.split('_')[0] for f in os.listdir('.') if f.endswith('_EICL1st.md')]


def update_readme(content, start_marker, end_marker):
    try:
        start_index = content.find(start_marker)
        end_index = content.find(end_marker)
        if start_index == -1 or end_index == -1:
            logging.error(
                "Error: Couldn't find the table markers in README.md")
            return content

        table_content = content[start_index +
                                len(start_marker):end_index].strip()
        table_rows = table_content.split('\n')[2:]  # 跳过表头和分隔行

        new_table = [
            f'{start_marker}\n',
            '| EICL1st· Name | ' +
            ' | '.join(date.strftime("%-m.%-d")
                       for date in date_range) + ' |\n',
            '| ------------- | ' +
            ' | '.join(['----' for _ in date_range]) + ' |\n'
        ]

        existing_users = set()
        for row in table_rows:
            match = re.match(r'\|\s*([^|]+)\s*\|', row)
            if match:
                display_name = match.group(1).strip()
                existing_users.add(display_name)
                user_status = get_user_study_status(display_name)
                new_row = f"| {display_name} |"
                for date in date_range:
                    status = check_weekly_status(user_status, date)
                    new_row += f" {status} |"
                new_table.append(new_row + '\n')
            else:
                logging.warning(f"Skipping invalid row: {row}")

        # 添加新用户
        all_users = set(get_all_user_files())
        new_users = all_users - existing_users
        for user in new_users:
            user_status = get_user_study_status(user)
            new_row = f"| {user} |"
            for date in date_range:
                status = check_weekly_status(user_status, date)
                new_row += f" {status} |"
            new_table.append(new_row + '\n')
            logging.info(f"Added new user: {user}")

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

        new_content = update_readme(
            content, "<!-- START_COMMIT_TABLE -->", "<!-- END_COMMIT_TABLE -->")

        with open('README.md', 'w', encoding='utf-8') as file:
            file.write(new_content)

        logging.info("README.md has been successfully updated.")
    except Exception as e:
        logging.error(f"An error occurred in main function: {str(e)}")


if __name__ == "__main__":
    main()
