"""
根据匹配结果填回html中
"""
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import normalize
from collections import defaultdict
import numpy as np
import faiss
import json
import re
import warnings

# 忽略 FutureWarning 警告
warnings.simplefilter(action='ignore', category=FutureWarning)
# 使用轻量级BERT模型进行语义相似度分析
model = SentenceTransformer('paraphrase-MiniLM-L3-v2')
similarity_method = "MINILLM"

# checkbox相对阈值分位数
checkbox_threshold_quantile = 0.2


# 清空html中已经填充的部分
def clear_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    for input_tag in soup.find_all('input'):
        input_attr = input_tag.attrs
        if 'value' in input_attr:
            del input_attr['value']
        if 'checked' in input_attr:
            del input_attr['checked']

    # 清除所有select标签中选中的option
    for select_tag in soup.find_all('select'):
        for option_tag in select_tag.find_all('option'):
            if 'selected' in option_tag.attrs:
                del option_tag.attrs['selected']

    return str(soup.prettify())


# 判断匹配出来的字段是否在student_data中
def is_in_student_data(result, student_data):
    if type(result['Key']) is list:  # 对多字段匹配到的学生数据进行简单拼接
        value = ' '.join([student_data[key] for key in result['Key'] if key in student_data])
        return value
    elif type(result['Key']) is str:
        if result['Key'] in student_data:
            return student_data[result['Key']]
    return None


class BS_fill_js:
    def __init__(self, result, html, student_data, test_U):
        self.soup = BeautifulSoup(html, 'html.parser')
        self.test_result = result
        self.data = student_data
        self.test_U = test_U
        self.fill_set = {"input": {},
                         "checkbox_radio": [],
                         "select": {}}

    # 填充input标签的内容
    def input_field_fill(self, match_result, student_data):
        for result in match_result:
            if 'Key' in result and 'Tag' in result and result['Tag'] == 'input':
                student_value = is_in_student_data(result, student_data)
                if student_value and 'Id' in result:
                    # 获取input标签
                    input_tag = self.soup.find(result['Tag'], {'id': result['Id']})
                    if input_tag and input_tag.get('type') != 'radio' and input_tag.get('type') != 'checkbox' \
                            and result['Id'] not in self.fill_set["input"].keys():
                        # 如果该input标签的类型不是checkbox和radio，就填充对应文本
                        self.fill_set["input"][result['Id']] = student_value

    # 填充select标签的内容
    def select_field_fill(self, match_result, student_data):
        for result in match_result:
            if 'Key' in result and 'Tag' in result and result['Tag'] == 'select':
                student_value = is_in_student_data(result, student_data)
                if student_value and 'Id' in result:
                    # 获取select标签
                    select_tag = self.soup.find(result['Tag'], {'id': result['Id']})
                    if select_tag:
                        # 获取select标签的所有属性
                        select_attrs = select_tag.attrs
                        # 如果该属性是disabled或者hidden的，就不进行填充
                        if 'disabled' in select_attrs or 'hidden' in select_attrs:
                            continue
                        # 根据语义分析结果进行选择
                        most_similar_option = option_analysis(student_value, select_tag)
                        if most_similar_option:
                            self.fill_set['select'][result['Id']] = most_similar_option.get("value", most_similar_option.text)

    # 填充textarea标签的内容
    def textarea_field_fill(self, match_result, student_data):
        for result in match_result:
            if 'Key' in result and 'Tag' in result and result['Tag'] == 'textarea':
                student_value = is_in_student_data(result, student_data)
                if student_value and 'Id' in result:
                    # 获取textarea标签
                    textarea_tag = self.soup.find(result['Tag'], {'id': result['Id']})
                    if textarea_tag and result['Id'] not in self.fill_set['input'].keys():
                        # 获取textarea标签的所有属性
                        self.fill_set['input'][result['Id']] = student_value

    # 根据checkbox或者radio中的内容进行语义相似度分析并勾选相应选项
    def checkbox_radio_field_fill(self, match_result, student_data, test_U):
        checkbox_dict, radio_dict = input_field_process(match_result, test_U)
        checkbox_checked_id, radio_checked_id = find_fill_id(checkbox_dict, radio_dict, student_data)
        # 根据勾选的选项id进行勾选
        for checkbox_id in checkbox_checked_id:
            checkbox_tag = self.soup.find('input', {'id': checkbox_id})
            if checkbox_tag:
                self.fill_set['checkbox_radio'].append(checkbox_id)
        for radio_id in radio_checked_id:
            radio_tag = self.soup.find('input', {'id': radio_id})
            if radio_tag:
                self.fill_set['checkbox_radio'].append(radio_id)

    def Fill(self):
        # 处理input
        self.input_field_fill(self.test_result, self.data)
        # 处理checkbox和radio
        self.checkbox_radio_field_fill(self.test_result, self.data, self.test_U)
        # 处理select
        self.select_field_fill(self.test_result, self.data)
        # 处理textarea
        self.textarea_field_fill(self.test_result, self.data)

        return self.fill_set


# class BS_fill:
#     def __init__(self, result, html, student_data, test_U):
#         html = clear_html(html)
#         self.test_html = html
#         self.test_result = result
#         self.data = student_data
#         self.test_U = test_U
#
#     # 填充input标签的内容
#     @staticmethod
#     def input_field_fill(match_result, soup, student_data):
#         for result in match_result:
#             if 'Key' in result and 'Tag' in result and result['Tag'] == 'input':
#                 student_value = is_in_student_data(result, student_data)
#                 if student_value and 'Id' in result:
#                     # 获取input标签
#                     input_tag = soup.find(result['Tag'], {'id': result['Id']})
#                     if input_tag and input_tag.get('type') != 'radio' and input_tag.get('type') != 'checkbox':
#                         # 如果该input标签的类型不是checkbox和radio，就填充对应文本
#                         input_tag['value'] = student_value
#         soup = soup.prettify()
#         return soup
#
#     # 填充select标签的内容
#     @staticmethod
#     def select_field_fill(match_result, soup,  student_data):
#         for result in match_result:
#             if 'Key' in result and 'Tag' in result and result['Tag'] == 'select':
#                 student_value = is_in_student_data(result, student_data)
#                 if student_value and 'Id' in result:
#                     # 获取select标签
#                     select_tag = soup.find(result['Tag'], {'id': result['Id']})
#                     if select_tag:
#                         # 获取select标签的所有属性
#                         select_attrs = select_tag.attrs
#                         # 如果该属性是disabled或者hidden的，就不进行填充
#                         if 'disabled' in select_attrs or 'hidden' in select_attrs:
#                             continue
#                         # 根据语义分析结果进行选择
#                         most_similar_option = option_analysis(student_value, select_tag)
#                         if most_similar_option:
#                             most_similar_option['selected'] = 'selected'
#         soup = soup.prettify()
#         return soup
#
#     # 填充textarea标签的内容
#     @staticmethod
#     def textarea_field_fill(match_result, soup, student_data):
#         for result in match_result:
#             if 'Key' in result and 'Tag' in result and result['Tag'] == 'textarea':
#                 student_value = is_in_student_data(result, student_data)
#                 if student_value and 'Id' in result:
#                     # 获取textarea标签
#                     textarea_tag = soup.find(result['Tag'], {'id': result['Id']})
#                     if textarea_tag:
#                         # 获取textarea标签的所有属性
#                         textarea_tag.string = student_value
#         soup = soup.prettify()
#         return soup
#
#     # 根据checkbox或者radio中的内容进行语义相似度分析并勾选相应选项
#     @staticmethod
#     def checkbox_radio_field_fill(match_result, soup, student_data, test_U):
#         checkbox_dict, radio_dict = input_field_process(match_result, test_U)
#         checkbox_checked_id, radio_checked_id = find_fill_id(checkbox_dict, radio_dict, student_data)
#         # 根据勾选的选项id进行勾选
#         for checkbox_id in checkbox_checked_id:
#             checkbox_tag = soup.find('input', {'id': checkbox_id})
#             if checkbox_tag:
#                 checkbox_tag.attrs['checked'] = 'checked'
#         for radio_id in radio_checked_id:
#             radio_tag = soup.find('input', {'id': radio_id})
#             if radio_tag:
#                 radio_tag.attrs['checked'] = 'checked'
#         soup = soup.prettify()
#         return soup
#
#     def Fill(self):
#         # 填充input
#         s_input = BeautifulSoup(self.test_html, 'html.parser')
#         filled_html = str(self.input_field_fill(self.test_result, s_input, self.data))
#         # 填充checkbox和radio
#         s_checkbox_radio = BeautifulSoup(filled_html, 'html.parser')
#         filled_html = str(self.checkbox_radio_field_fill(self.test_result, s_checkbox_radio, self.data, self.test_U))
#         # 填充select
#         s_select = BeautifulSoup(filled_html, 'html.parser')
#         filled_html = str(self.select_field_fill(self.test_result, s_select, self.data))
#         # 填充textarea
#         s_textarea = BeautifulSoup(filled_html, 'html.parser')
#         filled_html = str(self.textarea_field_fill(self.test_result, s_textarea, self.data))
#         filled_html = re.sub(r'\s+', ' ', filled_html.replace("\n", "")).strip()
#         return filled_html


# 计算文本与另一个文本列表（所有选项）之间的语义相似度
def calculate_semantic_similarity(target_text, text_list, use_threshold=False, method='MINILLM'):
    """
    通过轻量级BERT模型编码为向量，并利用归一化计算内积等效于计算余弦相似度
    :param target_text: 学生的数据，用于比较
    :param text_list: html中的选项列表
    :param use_threshold: 用于判断是否计算checkbox的相似度相对阈值，大于该相对阈值时将对应checkbox标记为选中
    :param method: 使用的计算方法，默认为'MINILLM'表示轻量级BERT，可选'rapidfuzz'表示rapidfuzz
    :return: 最高相似度的选项文本或符合相似度阈值的文本列表
    """
    if method == 'MINILLM':
        # 预先把文本列表编码为向量并归一化
        text_embeddings = model.encode(text_list)
        text_embeddings_normalized = normalize(text_embeddings)
        # 创建faiss索引
        dimension = text_embeddings_normalized.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(text_embeddings_normalized)
        target_embedding = model.encode([target_text])
        target_embedding_normalized = normalize(target_embedding)

        # 判断checkbox高于相似度阈值的选项
        if use_threshold:
            distances, indices = index.search(target_embedding_normalized, len(text_list))
            # 将所有相似度进行归一化得出相对阈值
            threshold = np.quantile(distances[0], 1 - checkbox_threshold_quantile)
            return [text_list[indices[0][i]] for i in range(len(text_list)) if distances[0][i] >= threshold]
        # 搜索与目标文本最相似的文本
        distances, indices = index.search(target_embedding_normalized, 1)
        return text_list[indices[0][0]]

    elif method == 'rapidfuzz':
        from rapidfuzz import process, fuzz
        if use_threshold:
            fuzzy_result = process.extract(target_text, text_list, scorer=fuzz.partial_ratio)
            # 将所有相似度进行归一化得出相对阈值
            threshold = np.quantile([result[1] for result in fuzzy_result], 1 - checkbox_threshold_quantile)
            return [result[0] for result in fuzzy_result if result[1] >= threshold]
        fuzzy_result = process.extractOne(target_text, text_list, scorer=fuzz.partial_ratio)
        return fuzzy_result[0]


# 根据option中的内容进行语义相似度分析
def option_analysis(value, select_tag):
    options_text = {}
    # 获取select标签的所有option
    for option in select_tag.find_all('option'):
        options_text[re.sub(r'\s+', ' ', option.text).strip()] = option
    most_similar_option_text = calculate_semantic_similarity(value, list(options_text.keys()), method=similarity_method)
    return options_text[most_similar_option_text]


# 处理input标签(在已有解析结果找到所有具有Key值撇配的checkbox和radio标签)
def input_field_process(match_result, test_U):
    test_html_parse_result = json.load(open(f'./result/final/{test_U}_final_result.json', 'r', encoding='utf-8'))
    # 定义存储checkbox以及radio对应的学生数据以及其id的字典（格式为{key1: [id1, id2, ...], key2: [id3, id4, ...], ...}）
    checkbox_dict = defaultdict(list)
    radio_dict = defaultdict(list)
    # 将所有checkbox和radio类型的input标签提取出来
    checkbox_tags = {}
    radio_tags = {}
    for input_field in test_html_parse_result['input']:
        if input_field['Type'] == 'checkbox':
            checkbox_tags[input_field['Id']] = input_field
        elif input_field['Type'] == 'radio':
            radio_tags[input_field['Id']] = input_field
    # 在匹配结果中查找对应id的checkbox和radio的匹配Key
    for result in match_result:
        if 'Key' in result and 'Id' in result:
            # 获取checkbox和radio对应的Key
            Keys = []
            if type(result['Key']) is list:
                Keys.extend(result['Key'])
            elif type(result['Key']) is str:
                Keys.append(result['Key'])
            # 将checkbox和radio的Key存储在对应的字典中
            if result['Id'] in checkbox_tags:
                for key in Keys:
                    checkbox_dict[key].append(checkbox_tags[result['Id']])
            elif result['Id'] in radio_tags:
                for key in Keys:
                    radio_dict[key].append(radio_tags[result['Id']])
    return checkbox_dict, radio_dict


# 存储radio和checkbox中需要勾选的选项id
def find_fill_id(checkbox_dict, radio_dict, student_data):
    checkbox_checked_id = set()
    radio_checked_id = set()
    # 将radio标签的选项标记为checked（单选，只需取最高语义相似度选项）
    for key, radio_fields in radio_dict.items():
        label_text_list = []
        for radio_field in radio_fields:
            label_text_list.append(radio_field['Label'])
        if key in student_data:
            most_similar_label_text = calculate_semantic_similarity(student_data[key], label_text_list,
                                                                    method=similarity_method)
            for radio_field in radio_fields:
                if radio_field['Label'] == most_similar_label_text and 'Id' in radio_field:
                    radio_checked_id.add(radio_field['Id'])
    # 将checkbox标签的选项标记为checked（多选，需要取所有语义相似度高于阈值的选项）
    for key, checkbox_fields in checkbox_dict.items():
        label_text_list = []
        for checkbox_field in checkbox_fields:
            label_text_list.append(checkbox_field['Label'])
        if key in student_data:
            # 处理多选情况（将学生数据中多选的选项分别分析相似度）
            if type(student_data[key]) is not str:
                most_similar_label_text = []
                for key_data in student_data[key]:
                    most_similar_label_text.append(
                        calculate_semantic_similarity(key_data, label_text_list, method=similarity_method))
            else:
                most_similar_label_text = calculate_semantic_similarity(student_data[key], label_text_list,
                                                                        use_threshold=True, method=similarity_method)
            for checkbox_field in checkbox_fields:
                if checkbox_field['Label'] in most_similar_label_text and 'Id' in checkbox_field:
                    checkbox_checked_id.add(checkbox_field['Id'])
    return checkbox_checked_id, radio_checked_id
