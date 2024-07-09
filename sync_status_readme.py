import os
import re
from datetime import datetime, timedelta
import pytz
import logging

# Constants
START_DATE = datetime(2024, 6, 24, tzinfo=pytz.UTC)
END_DATE = datetime(2024, 7, 14, tzinfo=pytz.UTC)
DEFAULT_TIMEZONE = 'Asia/Shanghai'
FILE_SUFFIX = '_EICL1st.md'
README_FILE = 'README.md'
Content_START_MARKER = "<!-- Content_START -->"
Content_END_MARKER = "<!-- Content_END -->"
TABLE_START_MARKER = "<!-- START_COMMIT_TABLE -->"
TABLE_END_MARKER = "<!-- END_COMMIT_TABLE -->"

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def get_date_range():
    return [START_DATE + timedelta(days=x) for x in range((END_DATE - START_DATE).days + 1)]


def get_user_timezone(file_content):
    yaml_match = re.search(r'---\s*\ntimezone:\s*(\S+)\s*\n---', file_content)
    if yaml_match:
        try:
            return pytz.timezone(yaml_match.group(1))
        except pytz.exceptions.UnknownTimeZoneError:
            logging.warning(
                f"Unknown timezone: {yaml_match.group(1)}. Using default {DEFAULT_TIMEZONE}.")
    return pytz.timezone(DEFAULT_TIMEZONE)


def extract_content_between_markers(file_content):
    start_index = file_content.find(Content_START_MARKER)
    end_index = file_content.find(Content_END_MARKER)
    if start_index == -1 or end_index == -1:
        logging.warning("EICL1st markers not found in the file")
        return ""
    return file_content[start_index + len(Content_START_MARKER):end_index].strip()


def find_date_in_content(content, local_date):
    date_patterns = [
        r'###\s*' + local_date.strftime("%Y.%m.%d"),
        r'###\s*' + local_date.strftime("%Y.%m.%d").replace('.0', '.'),
        r'###\s*' +
        local_date.strftime("%m.%d").lstrip('0').replace('.0', '.'),
        r'###\s*' + local_date.strftime("%Y/%m/%d"),
        r'###\s*' + local_date.strftime("%m/%d").lstrip('0').replace('/0', '/')
    ]
    combined_pattern = '|'.join(date_patterns)
    return re.search(combined_pattern, content)


def get_content_for_date(content, start_pos):
    next_date_pattern = r'###\s*(\d{4}\.)?(\d{1,2}[\.\/]\d{1,2})'
    next_date_match = re.search(next_date_pattern, content[start_pos:])
    if next_date_match:
        return content[start_pos:start_pos + next_date_match.start()]
    return content[start_pos:]


def check_md_content(file_content, date, user_tz):
    try:
        content = extract_content_between_markers(file_content)
        local_date = date.astimezone(user_tz).replace(
            hour=0, minute=0, second=0, microsecond=0)
        current_date_match = find_date_in_content(content, local_date)

        if not current_date_match:
            logging.info(
                f"No match found for date {local_date.strftime('%Y-%m-%d')}")
            return False

        date_content = get_content_for_date(content, current_date_match.end())
        date_content = re.sub(r'\s', '', date_content)
        logging.info(
            f"Content length for {local_date.strftime('%Y-%m-%d')}: {len(date_content)}")
        return len(date_content) > 10
    except Exception as e:
        logging.error(f"Error in check_md_content: {str(e)}")
        return False


def get_user_study_status(nickname):
    user_status = {}
    file_name = f"{nickname}{FILE_SUFFIX}"
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            file_content = file.read()
        user_tz = get_user_timezone(file_content)
        logging.info(
            f"File content length for {nickname}: {len(file_content)} user_tz: {user_tz}")
        current_date = datetime.now(user_tz).replace(
            hour=0, minute=0, second=0, microsecond=0)

        for date in get_date_range():
            local_date = date.astimezone(user_tz).replace(
                hour=0, minute=0, second=0, microsecond=0)
            if local_date > current_date:
                user_status[date] = " "
            elif local_date == current_date:
                user_status[date] = "✅" if check_md_content(
                    file_content, date, user_tz) else " "
            else:
                user_status[date] = "✅" if check_md_content(
                    file_content, date, user_tz) else "⭕️"

        logging.info(f"Successfully processed file for user: {nickname}")
    except FileNotFoundError:
        logging.error(f"Error: Could not find file {file_name}")
        user_status = {date: "⭕️" for date in get_date_range()}
    except Exception as e:
        logging.error(
            f"Unexpected error processing file for {nickname}: {str(e)}")
        user_status = {date: "⭕️" for date in get_date_range()}
    return user_status


def check_weekly_status(user_status, date, user_tz):
    try:
        local_date = date.astimezone(user_tz).replace(
            hour=0, minute=0, second=0, microsecond=0)
        week_start = (local_date - timedelta(days=local_date.weekday()))
        week_dates = [week_start + timedelta(days=x) for x in range(7)]
        current_date = datetime.now(user_tz).replace(
            hour=0, minute=0, second=0, microsecond=0)
        week_dates = [d for d in week_dates if d.astimezone(pytz.UTC).date() in [
            date.date() for date in get_date_range()] and d <= min(local_date, current_date)]

        missing_days = sum(1 for d in week_dates if user_status.get(datetime.combine(
            d.astimezone(pytz.UTC).date(), datetime.min.time()).replace(tzinfo=pytz.UTC), "⭕️") == "⭕️")

        if local_date == current_date and missing_days > 2:
            return "❌"
        elif local_date < current_date and missing_days > 2:
            return "❌"
        elif local_date > current_date:
            return " "
        else:
            return user_status.get(datetime.combine(date.date(), datetime.min.time()).replace(tzinfo=pytz.UTC), "⭕️")
    except Exception as e:
        logging.error(f"Error in check_weekly_status: {str(e)}")
        return "⭕️"


def get_all_user_files():
    return [f.split('_')[0] for f in os.listdir('.') if f.endswith(FILE_SUFFIX)]


def update_readme(content):
    try:
        start_index = content.find(TABLE_START_MARKER)
        end_index = content.find(TABLE_END_MARKER)
        if start_index == -1 or end_index == -1:
            logging.error(
                "Error: Couldn't find the table markers in README.md")
            return content

        new_table = [
            f'{TABLE_START_MARKER}\n',
            '| EICL1st· Name | ' +
            ' | '.join(date.strftime("%m.%d").lstrip('0')
                       for date in get_date_range()) + ' |\n',
            '| ------------- | ' +
            ' | '.join(['----' for _ in get_date_range()]) + ' |\n'
        ]

        existing_users = set()
        table_rows = content[start_index +
                             len(TABLE_START_MARKER):end_index].strip().split('\n')[2:]

        for row in table_rows:
            match = re.match(r'\|\s*([^|]+)\s*\|', row)
            if match:
                display_name = match.group(1).strip()
                existing_users.add(display_name)
                new_table.append(generate_user_row(display_name))
            else:
                logging.warning(f"Skipping invalid row: {row}")

        new_users = set(get_all_user_files()) - existing_users
        for user in new_users:
            new_table.append(generate_user_row(user))
            logging.info(f"Added new user: {user}")

        new_table.append(f'{TABLE_END_MARKER}\n')
        return content[:start_index] + ''.join(new_table) + content[end_index + len(TABLE_END_MARKER):]
    except Exception as e:
        logging.error(f"Error in update_readme: {str(e)}")
        return content

# def generate_user_row(user):
#     user_status = get_user_study_status(user)
#     with open(f"{user}{FILE_SUFFIX}", 'r', encoding='utf-8') as file:
#         file_content = file.read()
#     user_tz = get_user_timezone(file_content)
#     new_row = f"| {user} |"
#     is_eliminated = False
#     for date in get_date_range():
#         if is_eliminated:
#             new_row += " |"
#         else:
#             status = check_weekly_status(user_status, date, user_tz)
#             if status == "❌":
#                 is_eliminated = True
#             new_row += f" {status} |"
#     return new_row + '\n'


def generate_user_row(user):
    user_status = get_user_study_status(user)
    with open(f"{user}{FILE_SUFFIX}", 'r', encoding='utf-8') as file:
        file_content = file.read()
    user_tz = get_user_timezone(file_content)
    new_row = f"| {user} |"
    is_eliminated = False
    absent_count = 0
    current_week = None

    user_current_day = datetime.now(user_tz).replace(
            hour=0, minute=0, second=0, microsecond=0)
    for date in get_date_range():
        # 获取用户时区和当地时间进行比较，如果用户打卡时间大于当地时间，则不显示
        user_datetime = date.astimezone(pytz.UTC).replace(
                hour=0, minute=0, second=0, microsecond=0)
        if is_eliminated or user_datetime > user_current_day:
            new_row += " |"
        else:
            user_date = user_datetime
            # 检查是否是新的一周
            week = user_date.isocalendar()[1]  # 获取ISO日历周数
            if week != current_week:
                current_week = week
                absent_count = 0  # 重置缺勤计数

            status = user_status.get(user_date, "")

            if status == "⭕️":
                absent_count += 1
                if absent_count > 2:
                    is_eliminated = True
                    new_row += " ❌ |"
                else:
                    new_row += " ⭕️ |"
            else:
                new_row += f" {status} |"

    return new_row + '\n'


def main():
    try:
        with open(README_FILE, 'r', encoding='utf-8') as file:
            content = file.read()
        new_content = update_readme(content)
        with open(README_FILE, 'w', encoding='utf-8') as file:
            file.write(new_content)
        logging.info("README.md has been successfully updated.")
    except Exception as e:
        logging.error(f"An error occurred in main function: {str(e)}")


if __name__ == "__main__":
    main()
