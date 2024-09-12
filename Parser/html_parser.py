import re
import json
from bs4 import BeautifulSoup

test_U = "nyu"
html_path = f'test_data/{test_U}_test.html'
with open(html_path, 'r', encoding='utf-8') as f:
    local_html = f.read()


def bs_parser(html):
    soup = BeautifulSoup(html, 'html.parser')
    # 提取所有输入字段并进行定位
    input_fields = html_parser_input(soup)
    select_fields = html_parser_select(soup)
    textarea_fields = html_parser_textarea(soup)
    parse_result = {
        'input': input_fields,
        'select': select_fields,
        'textarea': textarea_fields
    }

    return parse_result


parsed_ids = set()  # 记录已经解析过的input


# 解析input标签
def html_parser_input(soup):
    input_fields = []
    for input_field in soup.find_all('input'):
        if input_field.get('type') == 'checkbox':
            input_fields.append(
                html_parser_checkbox(input_field)
            )
        else:
            input_fields.append({
                'Tag': input_field.name,
                'Name': input_field.get('name'),
                'Id': input_field.get('id'),
                'Type': input_field.get('type'),
                'Required': input_field.get('required'),
                'Children': []
            })

    return input_fields


# 解析checkbox类型的input标签
def html_parser_checkbox(checkbox_field):
    checkbox_field_dict = {
        'Tag': checkbox_field.name,
        'Name': checkbox_field.get('name'),
        'Id': checkbox_field.get('id'),
        'Type': checkbox_field.get('type'),
        'Required': checkbox_field.get('required'),
        'Children': []
    }

    return checkbox_field_dict


# 解析select标签和datalist标签
def html_parser_select(soup):
    select_fields = []
    for select_field in soup.find_all(['select', 'datalist']):
        options = select_field.find_all('option')
        if len(options) > 0 and (not (len(options) == 1 and options[0].text.strip() == '')):
            select_fields.append({
                'Tag': select_field.name,
                'Name': select_field.get('name'),
                'Id': select_field.get('id'),
                'Class': select_field.get('class'),
                'Disabled': select_field.get('disabled'),
                'Options': [{'Value': option.get('value'),
                             'Text': re.sub(r'\s+', ' ', option.text).strip()} for option in options],
                'Required': select_field.get('required'),
                'Children': []
            })
    return select_fields


# 解析textarea标签
def html_parser_textarea(soup):
    textarea_fields = []
    for textarea_field in soup.find_all('textarea'):
        textarea_fields.append({
            'Tag': textarea_field.name,
            'Name': textarea_field.get('name'),
            'Id': textarea_field.get('id'),
            'Required': textarea_field.get('required'),
            'Children': []
        })

    return textarea_fields


# 利用AI解析的结果和bs解析的结果,匹配生成最终解析结果
def html_parser(bs_path, ai_path, result_path):
    with open(bs_path, 'w') as f:
        json.dump(bs_parser(local_html), f)
    with open(bs_path, 'r') as f:
        bs_result = json.load(f)
    with open(ai_path, 'r') as f:
        ai_results = json.load(f)
    # 提取AI解析的所有结果
    all_ai_result = {'input': [], 'select': [], 'textarea': []}

    # 递归遍历所有子节点,直至找到含有input,select,datalist和textarea tag的元素
    def find_field_all_result(field):
        if field['Tag'] == 'input':
            all_ai_result['input'].append(field)
            return
        elif field['Tag'] == 'select' or field['Tag'] == 'datalist':
            # 将在Children中的options删除
            field['Children'] = []
            all_ai_result['select'].append(field)
            return
        elif field['Tag'] == 'textarea':
            all_ai_result['textarea'].append(field)
            return
        else:
            for child in field['Children']:
                find_field_all_result(child)

    for ai_result in ai_results:
        for ai in ai_result['data']:
            find_field_all_result(ai)

    # 将AI解析的结果与bs解析的结果进行匹配
    for input_field in bs_result['input']:
        for ai_field in all_ai_result['input']:
            if input_field['Id'] == ai_field['Id'] and ai_field['Tag'] == 'input':
                input_field['Children'] = ai_field['Children']
                input_field['Label'] = ai_field['Label']

    for select_field in bs_result['select']:
        for ai_field in all_ai_result['select']:
            if 'Id' in select_field and 'Id' in ai_field:
                if (select_field['Id'] == ai_field['Id']
                        and (ai_field['Tag'] == 'select' or ai_field['Tag'] == 'datalist')):
                    select_field['Children'] = ai_field['Children']
                    select_field['Label'] = ai_field['Label']
            elif 'Name' in select_field and 'Name' in ai_field:
                if (select_field['Name'] == ai_field['Name'] and
                        (ai_field['Tag'] == 'select' or ai_field['Tag'] == 'datalist')):
                    select_field['Children'] = ai_field['Children']
                    select_field['Label'] = ai_field['Label']

    for textarea_field in bs_result['textarea']:
        for ai_field in all_ai_result['textarea']:
            if textarea_field['Id'] == ai_field['Id'] and ai_field['Tag'] == 'textarea':
                textarea_field['Children'] = ai_field['Children']
                textarea_field['Label'] = ai_field['Label']

    # 去除重复项,即没有Label属性的项
    def remove_no_label_field(field_list):
        return [field for field in field_list if field.get('Label')]

    bs_result['input'] = remove_no_label_field(bs_result['input'])
    bs_result['select'] = remove_no_label_field(bs_result['select'])
    bs_result['textarea'] = remove_no_label_field(bs_result['textarea'])

    with open(result_path, 'w') as f:
        json.dump(bs_result, f)


if __name__ == '__main__':
    # with open("result/bs/emory_bs_result.json", 'w') as f:
    #     json.dump(bs_parser(local_html), f)
    html_parser(f"result/bs/{test_U}_bs_result.json",
                f"result/AI/{test_U}_result.json",
                f"result/final/{test_U}_final_result.json")
