import json
import re
from bs4 import BeautifulSoup
from html_parser import bs_parser
from AI_parser import chunks_with_overlap, generate_messages, extract_relevant_context, unnecessary_tags
from AI_match import AI_match


# AI解析
def AI_parser(html, test_U):
    soup = BeautifulSoup(html, "html.parser")

    # 移除不必要的标签
    for tag in soup(unnecessary_tags):
        tag.decompose()

    # 保留select中的选项至多3个
    for select in soup.select('select'):
        options = select.find_all('option')
        if len(options) > 3:
            for option in options[3:]:
                option.decompose()

    save_attrs = ['class', 'id', 'name', 'type', 'for', 'onchange', 'onclick']
    # 将所有元素中的多余属性删除
    for tag in soup.find_all(True):
        if tag.attrs:
            tag.attrs = {k: v for k, v in tag.attrs.items() if k in save_attrs}

    soup = soup.prettify()

    # 获取精简后的HTML,去除冗余空格和换行符
    cleaned_html = re.sub(r'\s+', ' ', str(soup).replace("\n", "")).strip()
    # 将HTML中的注释删除
    cleaned_html = re.sub(r'<!--.*?-->', '', cleaned_html, flags=re.DOTALL)

    with open(f"./test_data/cleaned/{test_U}_cleaned.html", "w", encoding="utf-8") as f:
        f.write(cleaned_html)

    chunks = chunks_with_overlap(cleaned_html, 15000, 5000)
    previous_messages = None
    results = []
    all_input_tokens = 0
    all_output_tokens = 0
    for chunk in chunks:
        result, output_tokens, input_tokens = generate_messages(chunk, previous_messages)
        all_input_tokens += input_tokens
        all_output_tokens += output_tokens
        result = json.loads(result)
        previous_messages = extract_relevant_context(result)
        results.append(result)

    print("输入token数:", all_input_tokens)
    print("输出token数:", all_output_tokens)
    print("总token数:", all_input_tokens + all_output_tokens)

    with open(f'result/AI/{test_U}_result.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)


# 利用AI解析的结果和bs解析的结果,匹配生成最终解析结果
def html_parser(html, test_U):
    bs_path = f'./result/bs/{test_U}_bs_result.json'
    ai_path = f'./result/AI/{test_U}_result.json'
    result_path = f'./result/final/{test_U}_final_result.json'
    with open(bs_path, 'w') as f:
        json.dump(bs_parser(html), f, indent=4)
    with open(bs_path, 'r') as f:
        bs_result = json.load(f)
    with open(ai_path, 'r') as f:
        ai_results = json.load(f)
    # 提取AI解析的所有结果
    all_ai_result = {'input': [], 'select': [], 'textarea': []}

    # 递归遍历所有子节点,直至找到含有input,select,datalist和textarea tag的元素
    def find_field_all_result(field):
        if 'Children' not in field or len(field['Children']) == 0:
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
            if input_field['Id'] == ai_field['Id']:
                # input_field['Children'] = ai_field['Children']
                input_field['Label'] = ai_field['Label']
                break

    for select_field in bs_result['select']:
        for ai_field in all_ai_result['select']:
            if 'Id' in select_field and 'Id' in ai_field:
                if select_field['Id'] == ai_field['Id']:
                    # select_field['Children'] = ai_field['Children']
                    select_field['Label'] = ai_field['Label']
                    break
            elif 'Name' in select_field and 'Name' in ai_field:
                if select_field['Name'] == ai_field['Name']:
                    # select_field['Children'] = ai_field['Children']
                    select_field['Label'] = ai_field['Label']
                    break

    for textarea_field in bs_result['textarea']:
        for ai_field in all_ai_result['textarea']:
            if textarea_field['Id'] == ai_field['Id'] and ai_field['Tag'] == 'textarea':
                # textarea_field['Children'] = ai_field['Children']
                textarea_field['Label'] = ai_field['Label']
                break

    no_label_set = []

    # 去除重复项,即没有Label属性或者Options属性的项
    def remove_no_label_field(field_list):
        result = []
        for field in field_list:
            if field.get('Label') or field.get('Options'):
                result.append(field)
            else:
                no_label_set.append(field)
        return result

    bs_result['input'] = remove_no_label_field(bs_result['input'])
    bs_result['select'] = remove_no_label_field(bs_result['select'])
    bs_result['textarea'] = remove_no_label_field(bs_result['textarea'])

    with open(result_path, 'w') as f:
        json.dump(bs_result, f, indent=4)


# 处理测试用例
def read_Utest_json(test_U):
    Utest_json = json.load(open(f'./result/final/{test_U}_final_result.json', 'r', encoding='utf-8'))
    unnecessary_key = ['Type', 'Required', 'Options', 'Disabled']
    Utest = []
    # 删除不需要的键值对
    for input_field in Utest_json['input']:
        for key in unnecessary_key:
            if key in input_field:
                input_field.pop(key)
        Utest.append(input_field)
    for select_field in Utest_json['select']:
        for key in unnecessary_key:
            if key in select_field:
                select_field.pop(key)
        Utest.append(select_field)
    for textarea_field in Utest_json['textarea']:
        for key in unnecessary_key:
            if key in textarea_field:
                textarea_field.pop(key)
        Utest.append(textarea_field)
    return Utest


# AI匹配
def Match(test_U):
    data = json.load(open('./data/Student_data.json', 'r', encoding='utf-8'))
    Utest = read_Utest_json(test_U)
    results = AI_match(Utest, data[-1])
    with open(f'./results/{test_U}_result.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
