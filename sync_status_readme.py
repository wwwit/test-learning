import os
import re
from datetime import datetime, timedelta
import pytz
import logging
import time

# 设置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# 设置UTC时区
utc_tz = pytz.UTC

# 定义日期范围（从6月24日到7月14日）
start_date = datetime(2024, 6, 24, tzinfo=utc_tz)
end_date = datetime(2024, 7, 14, tzinfo=utc_tz)
date_range = [start_date + timedelta(days=x)
              for x in range((end_date - start_date).days + 1)]


def get_user_timezone(file_content):
    # 尝试从 YAML 前置元数据中获取时区
    yaml_match = re.search(r'---\s*\ntimezone:\s*(\S+)\s*\n---', file_content)
    if yaml_match:
        timezone_str = yaml_match.group(1)
        try:
            return pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            logging.warning(
                f"Unknown timezone: {timezone_str}. Using default Asia/Shanghai.")

    # 如果没找到或无效，返回默认时区（中国标准时间）
    return pytz.timezone('Asia/Shanghai')


def check_md_content(file_content, date, user_tz):
    try:
        # 查找标记之间的内容
        start_marker = "<!-- Content_START -->"
        end_marker = "<!-- Content_END -->"
        start_index = file_content.find(start_marker)
        end_index = file_content.find(end_marker)

        if start_index == -1 or end_index == -1:
            logging.warning("EICL1st markers not found in the file")
            return False

        # 提取标记之间的内容
        content = file_content[start_index +
                               len(start_marker):end_index].strip()

        # 转换日期到用户时区
        local_date = date.astimezone(user_tz).replace(
            hour=0, minute=0, second=0, microsecond=0)

        # 在提取的内容中查找日期
        # date_patterns = [
        #     r'###\s*' + local_date.strftime("%Y.%m.%d"),
        #     r'###\s*' + local_date.strftime("%Y.%-m.%-d"),
        #     r'###\s*' + local_date.strftime("%-m.%-d"),
        #     r'###\s*' + local_date.strftime("%Y/%m/%d"),
        #     r'###\s*' + local_date.strftime("%-m/%-d")
        # ]
        date_patterns = [
            r'###\s*' + local_date.strftime("%Y.%m.%d"),
            r'###\s*' + local_date.strftime("%Y.%m.%d").replace('.0', '.'),
            r'###\s*' +
            local_date.strftime("%m.%d").lstrip('0').replace('.0', '.'),
            r'###\s*' + local_date.strftime("%Y/%m/%d"),
            r'###\s*' +
            local_date.strftime("%m/%d").lstrip('0').replace('/0', '/')
        ]

        combined_pattern = '|'.join(date_patterns)
        current_date_match = re.search(combined_pattern, content)

        if not current_date_match:
            logging.info(
                f"No match found for date {local_date.strftime('%Y-%m-%d')}")
            return False

        start_pos = current_date_match.end()
        next_date_pattern = r'###\s*(\d{4}\.)?(\d{1,2}[\.\/]\d{1,2})'
        next_date_match = re.search(next_date_pattern, content[start_pos:])

        if next_date_match:
            end_pos = start_pos + next_date_match.start()
            date_content = content[start_pos:end_pos]
        else:
            date_content = content[start_pos:]

        date_content = re.sub(r'\s', '', date_content)
        logging.info(
            f"Content length for {local_date.strftime('%Y-%m-%d')}: {len(date_content)}")
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

        # 获取用户时区
        user_tz = get_user_timezone(file_content)

        logging.info(
            f"File content length for {nickname}: {len(file_content)}")
        current_date = datetime.now(user_tz).replace(
            hour=0, minute=0, second=0, microsecond=0)
        for date in date_range:
            local_date = date.astimezone(user_tz).replace(
                hour=0, minute=0, second=0, microsecond=0)
            if local_date > current_date:
                user_status[date] = " "  # 未来的日期显示为空白
            elif local_date == current_date:
                user_status[date] = "✅" if check_md_content(
                    file_content, date, user_tz) else " "  # 当天有内容标记✅,否则空白
            else:
                user_status[date] = "✅" if check_md_content(
                    file_content, date, user_tz) else "⭕️"
        logging.info(f"Successfully processed file for user: {nickname}")
    except FileNotFoundError:
        logging.error(f"Error: Could not find file {file_name}")
        user_status = {date: "⭕️" for date in date_range}
    except Exception as e:
        logging.error(
            f"Unexpected error processing file for {nickname}: {str(e)}")
        user_status = {date: "⭕️" for date in date_range}
    return user_status


def check_weekly_status(user_status, date, user_tz):
    try:
        local_date = date.astimezone(user_tz).replace(
            hour=0, minute=0, second=0, microsecond=0)
        week_start = (local_date - timedelta(days=local_date.weekday()))
        week_dates = [week_start + timedelta(days=x) for x in range(7)]

        # 只考虑到当前日期为止的日期
        current_date = datetime.now(user_tz).replace(
            hour=0, minute=0, second=0, microsecond=0)
        week_dates = [d for d in week_dates if d.astimezone(utc_tz).date() in [date.date() for date in date_range]
                      and d <= min(local_date, current_date)]

        missing_days = 0
        for d in week_dates:
            # 将日期转换为与 user_status 键匹配的格式
            date_key = datetime.combine(d.astimezone(
                utc_tz).date(), datetime.min.time()).replace(tzinfo=utc_tz)
            status = user_status.get(date_key, "⭕️")
            print(f"Date: {d}, Status: {status}")
            if status == "⭕️":
                missing_days += 1

        print(f"Total missing days: {missing_days}")

        # 检查是否已经被淘汰
        if any(user_status.get(datetime.combine(d.date(), datetime.min.time()).replace(tzinfo=utc_tz), "") == "❌" for d in date_range if d < date):
            return "❌"

        # 如果本周缺勤超过两次，标记为淘汰
        if missing_days > 2:
            return "❌"

        return user_status.get(datetime.combine(date.date(), datetime.min.time()).replace(tzinfo=utc_tz), "⭕️")
    except Exception as e:
        logging.error(f"Error in check_weekly_status: {str(e)}")
        return "⭕️"


def check_overall_status(user_status, date, user_tz):
    try:
        local_date = date.astimezone(user_tz).replace(
            hour=0, minute=0, second=0, microsecond=0)
        current_date = datetime.now(user_tz).replace(
            hour=0, minute=0, second=0, microsecond=0)

        # 计算总共缺勤天数
        missing_days = sum(1 for d in date_range
                           if d <= min(date, current_date) and
                           user_status.get(d, "⭕️") == "⭕️")
        # missing_days = 0
        # for d in week_dates:
        #     # 将日期转换为与 user_status 键匹配的格式
        #     date_key = datetime.combine(d.astimezone(
        #         utc_tz).date(), datetime.min.time()).replace(tzinfo=utc_tz)
        #     status = user_status.get(date_key, "⭕️")
        #     print(f"Date: {d}, Status: {status}")
        #     if status == "⭕️":
        #         missing_days += 1

        # 如果总共缺勤超过两次，标记为淘汰
        if missing_days > 2:
            return "❌"

        # 当天的状态
        if local_date == current_date:
            return user_status.get(date, " ")
        # 过去的日期
        elif local_date < current_date:
            return user_status.get(date, "⭕️")
        # 未来的日期
        else:
            return " "

    except Exception as e:
        logging.error(f"Error in check_overall_status: {str(e)}")
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
            ' | '.join(date.strftime("%m.%d").lstrip('0')
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
                with open(f"{display_name}_EICL1st.md", 'r', encoding='utf-8') as file:
                    file_content = file.read()
                user_tz = get_user_timezone(file_content)
                new_row = f"| {display_name} |"
                is_eliminated = False
                for date in date_range:
                    if is_eliminated:
                        new_row += "  |"  # 淘汰后的日期保持空白
                    else:
                        status = check_weekly_status(
                            user_status, date, user_tz)
                        if status == "❌":
                            is_eliminated = True
                        new_row += f" {status} |"
                new_table.append(new_row + '\n')
            else:
                logging.warning(f"Skipping invalid row: {row}")

        # 添加新用户
        all_users = set(get_all_user_files())
        new_users = all_users - existing_users
        for user in new_users:
            user_status = get_user_study_status(user)
            with open(f"{user}_EICL1st.md", 'r', encoding='utf-8') as file:
                file_content = file.read()
            user_tz = get_user_timezone(file_content)
            new_row = f"| {user} |"
            is_eliminated = False
            for date in date_range:
                if is_eliminated:
                    new_row += "  |"  # 淘汰后的日期保持空白
                else:
                    status = check_weekly_status(user_status, date, user_tz)
                    if status == "❌":
                        is_eliminated = True
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
