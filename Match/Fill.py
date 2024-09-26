"""
根据匹配结果填回html中
"""
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import normalize
from collections import defaultdict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import numpy as np
import faiss
import json
import re
import warnings
import Config

# 忽略 FutureWarning 警告
warnings.simplefilter(action='ignore', category=FutureWarning)
# 使用轻量级BERT模型进行语义相似度分析
model = SentenceTransformer('paraphrase-MiniLM-L3-v2')
test_U = 'emory'
test_html_parse_result = json.load(open(f'../result/final/{test_U}_final_result.json', 'r', encoding='utf-8'))
# checkbox相对阈值分位数
checkbox_threshold_quantile = 0.3


# 使用BeautifulSoup进行填回
class BS_fill:
    def __init__(self, result, html, student_data):
        self.test_html = html
        self.test_result = result
        self.data = student_data

    # 填充input标签的内容
    @staticmethod
    def input_field_fill(match_result, soup, student_data):
        for result in match_result:
            if 'Key' in result and 'Tag' in result and result['Tag'] == 'input':
                if result['Key'] in student_data and 'Id' in result:
                    # 获取input标签
                    input_tag = soup.find(result['Tag'], {'id': result['Id']})
                    if input_tag:
                        # 如果该input标签的类型不是checkbox和radio，就填充
                        if input_tag.get('type') != 'radio' and input_tag.get('type') != 'checkbox':
                            input_tag.attrs['value'] = student_data[result['Key']]
        soup = soup.prettify()
        return soup

    # 填充select标签的内容
    @staticmethod
    def select_field_fill(match_result, soup, student_data):
        for result in match_result:
            if 'Key' in result and 'Tag' in result and result['Tag'] == 'select':
                if result['Key'] in student_data and 'Id' in result:
                    # 获取select标签
                    select_tag = soup.find(result['Tag'], {'id': result['Id']})
                    if select_tag:
                        # 获取select标签的所有属性
                        select_attrs = select_tag.attrs
                        # 如果该属性是disabled或者hidden的，就不进行填充
                        if 'disabled' in select_attrs or 'hidden' in select_attrs:
                            continue
                        # 获取对应的key值
                        student_value = student_data[result['Key']]
                        # 根据语义分析结果进行选择
                        most_similar_option = option_analysis(student_value, select_tag)
                        if most_similar_option:
                            most_similar_option['selected'] = 'selected'
        soup = soup.prettify()
        return soup

    # 填充textarea标签的内容
    @staticmethod
    def textarea_field_fill(match_result, soup, student_data):
        for result in match_result:
            if 'Key' in result and 'Tag' in result and result['Tag'] == 'textarea':
                if result['Key'] in student_data and 'Id' in result:
                    # 获取textarea标签
                    textarea_tag = soup.find(result['Tag'], {'id': result['Id']})
                    if textarea_tag:
                        # 获取textarea标签的所有属性
                        textarea_attrs = textarea_tag.attrs
                        # 如果该属性是disabled或者hidden的，就不进行填充
                        if 'disabled' in textarea_attrs or 'hidden' in textarea_attrs:
                            continue
                        textarea_tag.string = student_data[result['Key']]
        soup = soup.prettify()
        return soup

    # 根据checkbox或者radio中的内容进行语义相似度分析并勾选相应选项
    @staticmethod
    def checkbox_radio_field_fill(match_result, soup, student_data):
        checkbox_dict, radio_dict = input_field_process(match_result)
        checkbox_checked_id, radio_checked_id = find_fill_id(checkbox_dict, radio_dict, student_data)
        # 根据勾选的选项id进行勾选
        for checkbox_id in checkbox_checked_id:
            checkbox_tag = soup.find('input', {'id': checkbox_id})
            if checkbox_tag:
                checkbox_tag.attrs['checked'] = 'checked'
        for radio_id in radio_checked_id:
            radio_tag = soup.find('input', {'id': radio_id})
            if radio_tag:
                radio_tag.attrs['checked'] = 'checked'
        soup = soup.prettify()
        return soup

    def Fill(self):
        # 填充input
        s_input = BeautifulSoup(self.test_html, 'html.parser')
        filled_html = str(self.input_field_fill(self.test_result, s_input, self.data))
        # 填充checkbox和radio
        s_checkbox_radio = BeautifulSoup(filled_html, 'html.parser')
        filled_html = str(self.checkbox_radio_field_fill(self.test_result, s_checkbox_radio, self.data))
        # 填充select
        s_select = BeautifulSoup(filled_html, 'html.parser')
        filled_html = str(self.select_field_fill(self.test_result, s_select, self.data))
        # 填充textarea
        s_textarea = BeautifulSoup(filled_html, 'html.parser')
        filled_html = str(self.textarea_field_fill(self.test_result, s_textarea, self.data))
        with open(f'./filled/{test_U}_filled.html', 'w', encoding='utf-8') as f:
            f.write(filled_html)


# 使用Selenium进行填回
class SL_fill:
    def __init__(self, html_path, result, student_data, driver_path='./chromedriver.exe'):
        self.test_result = result
        self.data = student_data
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')
        self.server = webdriver.ChromeService(driver_path=driver_path)
        self.driver = webdriver.Chrome(options=options, service=self.server)
        # 加载本地 HTML 文件
        self.driver.get(html_path)

    # 填充input
    def input_field_fill(self, match_result, student_data):
        for result in match_result:
            if 'Key' in result and 'Tag' in result and result['Tag'] == 'input':
                if result['Key'] in student_data and 'Id' in result:
                    # 获取input标签
                    input_element = self.driver.find_element(By.ID, result['Id'])
                    if input_element:
                        if input_element.get_attribute('type') != 'checkbox' and input_element.get_attribute(
                                'type') != 'radio':
                            # 填充input
                            input_element.send_keys(student_data[result['Key']])

    # 填充select
    def select_field_fill(self, match_result, student_data):
        for result in match_result:
            if 'Key' in result and 'Tag' in result and result['Tag'] == 'select':
                if result['Key'] in student_data and 'Id' in result:
                    # 获取select标签
                    select_element = self.driver.find_element(By.ID, result['Id'])
                    if select_element:
                        # 获取对应的key值
                        student_value = student_data[result['Key']]
                        options_text = [option.text for option in select_element.find_elements(By.TAG_NAME, 'option')]
                        most_similar_text = calculate_semantic_similarity(student_value, options_text)
                        for option in select_element.find_elements(By.TAG_NAME, 'option'):
                            if option.text in most_similar_text:
                                option.click()

    # 填充textarea
    def textarea_field_fill(self, match_result, student_data):
        for result in match_result:
            if 'Key' in result and 'Tag' in result and result['Tag'] == 'textarea':
                if result['Key'] in student_data and 'Id' in result:
                    # 获取textarea标签
                    textarea_element = self.driver.find_element(By.ID, result['Id'])
                    # 填充textarea
                    textarea_element.send_keys(student_data[result['Key']])

    # 填充checkbox和radio
    def checkbox_radio_field_fill(self, match_result, student_data):
        checkbox_dict, radio_dict = input_field_process(match_result)
        checkbox_checked_id, radio_checked_id = find_fill_id(checkbox_dict, radio_dict, student_data)
        # 根据勾选的选项id进行勾选
        for checkbox_id in checkbox_checked_id:
            checkbox_element = self.driver.find_element(By.ID, checkbox_id)
            if checkbox_element:
                checkbox_element.click()
        for radio_id in radio_checked_id:
            radio_element = self.driver.find_element(By.ID, radio_id)
            if radio_element:
                radio_element.click()

    def Fill(self):
        # 填充input
        self.input_field_fill(self.test_result, self.data)
        # 填充select
        self.select_field_fill(self.test_result, self.data)
        # 填充textarea
        self.textarea_field_fill(self.test_result, self.data)
        # 填充checkbox和radio
        self.checkbox_radio_field_fill(self.test_result, self.data)
        with open(f'./filled/{test_U}_filled.html', 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        self.driver.quit()


# 计算文本与另一个文本列表（所有选项）之间的语义相似度
def calculate_semantic_similarity(target_text, text_list, use_threshold=False):
    """
    通过轻量级BERT模型编码为向量，并利用归一化计算内积等效于计算余弦相似度
    :param target_text: 学生的数据，用于比较
    :param text_list: html中的选项列表
    :param use_threshold: 用于判断是否计算checkbox的相似度相对阈值，大于该相对阈值时将对应checkbox标记为选中
    :return: 最高相似度的选项文本或符合相似度阈值的文本列表
    """
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


# 根据option中的内容进行语义相似度分析
def option_analysis(value, select_tag):
    options_text = {}
    # 获取select标签的所有option
    for option in select_tag.find_all('option'):
        options_text[re.sub(r'\s+', ' ', option.text).strip()] = option
    most_similar_option_text = calculate_semantic_similarity(value, list(options_text.keys()))
    return options_text[most_similar_option_text]


# 处理input标签(在已有解析结果找到所有具有Key值撇配的checkbox和radio标签)
def input_field_process(match_result):
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
        if 'Key' in result and 'Id' in result and result['Id'] in checkbox_tags:
            checkbox_dict[result['Key']].append(checkbox_tags[result['Id']])
        elif 'Key' in result and 'Id' in result and result['Id'] in radio_tags:
            radio_dict[result['Key']].append(radio_tags[result['Id']])
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
            most_similar_label_text = calculate_semantic_similarity(student_data[key], label_text_list)
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
                    most_similar_label_text.append(calculate_semantic_similarity(key_data, label_text_list))
            else:
                most_similar_label_text = calculate_semantic_similarity(student_data[key], label_text_list,
                                                                        use_threshold=True)
            for checkbox_field in checkbox_fields:
                if checkbox_field['Label'] in most_similar_label_text and 'Id' in checkbox_field:
                    checkbox_checked_id.add(checkbox_field['Id'])
    return checkbox_checked_id, radio_checked_id


if __name__ == '__main__':
    test_result = json.load(open(f'./results/{test_U}_result.json', 'r', encoding='utf-8'))
    test_html = open(f'../test_data/{test_U}_test.html', 'r', encoding='utf-8').read()
    data = json.load(open(f'./data/Student_data.json', 'r', encoding='utf-8'))[-1]
    # # BeautifulSoup填回html
    # BS_method = BS_fill(test_result, test_html, data)
    # BS_method.Fill()
    # Selenium填回html
    from webdriver_manager.chrome import ChromeDriverManager
    driver_path = ChromeDriverManager().install()
    Selenium_method = SL_fill(Config.PATH_OF_HTML, test_result, data,
                              driver_path=driver_path)
    Selenium_method.Fill()
