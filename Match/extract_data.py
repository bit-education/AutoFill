"""
简单向Notion数据库提取学生信息数据
"""

import json
from notion_client import Client

key = open('Secret_key.txt', 'r').read()
Id = open('Database_id.txt', 'r').read()


# 向Notion数据库提取信息
def extract_data(Database_id, secret_key):
    notion = Client(auth=secret_key)

    # 查询数据库内容
    response = notion.databases.query(database_id=Database_id)

    # 存储数据库中的数据
    extracted_data = []

    # 遍历每个学生条目
    for result in response['results']:
        # 提取每个条目的 'properties'，即列名
        properties = result['properties']
        # 存储当前条目的列名和对应的数据
        row_data = {}

        # 遍历每个列
        for column_name, column_value in properties.items():
            # 根据不同类型提取数据
            if column_value['type'] == 'title':
                # 如果是标题类型（可理解为主键），提取文本内容
                row_data[column_name] = column_value['title'][0]['text']['content'] if column_value['title'] else ""
            elif column_value['type'] == 'rich_text':
                # 提取富文本的内容
                row_data[column_name] = column_value['rich_text'][0]['text']['content'] if column_value[
                    'rich_text'] else ""
            elif column_value['type'] == 'number':
                # 提取数字内容
                row_data[column_name] = column_value['number']
            elif column_value['type'] == 'select':
                # 提取单选内容
                row_data[column_name] = column_value['select']['name'] if column_value['select'] else ""
            elif column_value['type'] == 'multi_select':
                # 提取多选内容
                row_data[column_name] = [item['name'] for item in column_value['multi_select']]
            elif column_value['type'] == 'date':
                # 提取日期内容
                row_data[column_name] = column_value['date']['start'] if column_value['date'] else ""
            elif column_value['type'] == 'email':
                # 提取邮件内容
                row_data[column_name] = column_value['email']
            elif column_value['type'] == 'phone_number':
                # 提取电话号码
                row_data[column_name] = column_value['phone_number']
            elif column_value['type'] == 'status':
                # 提取状态信息
                row_data[column_name] = column_value['status']['name'] if column_value['status'] else ""
            # 可以根据需要继续添加更多类型处理

        # 将解析后的行数据添加到列表中
        extracted_data.append(row_data)

    # 定义 JSON 文件保存路径
    json_file_path = './data/Student_data.json'

    # 将提取的数据写入 JSON 文件
    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(extracted_data, json_file, ensure_ascii=False, indent=4)

    print(f"数据已成功提取到 {json_file_path}")


if __name__ == '__main__':
    extract_data(Id, key)
