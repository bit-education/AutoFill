import re
import json
from bs4 import BeautifulSoup

html_path = 'test_data/yale_test.html'
with open(html_path, 'r', encoding='utf-8') as f:
    local_html = f.read()


def html_parser(html):
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

        if input_field.get('id') in parsed_ids:
            continue
        parsed_ids.add(input_field.get('id'))
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


# TODO:利用AI解析的结果和bs解析的结果,匹配生成最终的解析结果
def merge_result():
    with open('result/bs_result.json', 'r') as f:
        bs_result = json.load(f)
    with open('result/yale_result.json', 'r') as f:
        ai_result = json.load(f)

    for input_field in bs_result['input']:
        for ai_field in ai_result['data']:
            if input_field['Id'] == ai_field['id'] and ai_field['tag'] == 'input':
                input_field['Children'] = ai_field['Children']
                input_field['Label'] = ai_field['Label']

    for select_field in bs_result['select']:
        for ai_field in ai_result['data']:
            if select_field['Id'] == ai_field['id'] and ai_field['tag'] == 'select':
                select_field['Children'] = ai_field['Children']
                select_field['Label'] = ai_field['Label']

    for textarea_field in bs_result['textarea']:
        for ai_field in ai_result['data']:
            if textarea_field['Id'] == ai_field['id'] and ai_field['tag'] == 'textarea':
                textarea_field['Children'] = ai_field['Children']
                textarea_field['Label'] = ai_field['Label']

    with open('final_result.json', 'w') as f:
        json.dump(bs_result, f, indent=4)


if __name__ == '__main__':
    # with open("bs_result.json", "w") as f:
    #     json.dump(html_parser(local_html), f)
    merge_result()
