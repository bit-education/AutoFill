import json
import tiktoken
import re
from openai import OpenAI
from bs4 import BeautifulSoup

encoding = tiktoken.encoding_for_model("gpt-4")
headers = {"Content-Type": "application/json"}
local_html = open('test_data/yale_test.html', 'r', encoding='utf-8').read()
API_KEY = open('API_KEY.txt', 'r').read()
soup = BeautifulSoup(local_html, 'html.parser')
client = OpenAI(api_key=API_KEY)
unnecessary_tags = ['a', 'head', 'script', 'style', 'img', 'link', 'meta', 'footer', 'nav', 'hr', 'meter', 'object',
                    'noscript', 'video', 'canvas', 'picture', 'option', 'menu']


def AI_parser(html):
    soup = BeautifulSoup(html, "html.parser")

    # 移除不必要的标签
    for tag in soup(unnecessary_tags):
        tag.decompose()

    save_attrs = ['id', 'name', 'type', 'for', 'onchange', 'onclick']
    # 将所有元素中的多余属性删除
    for tag in soup.find_all(True):
        if tag.attrs:
            tag.attrs = {k: v for k, v in tag.attrs.items() if k in save_attrs}

    soup = soup.prettify()

    # 获取精简后的HTML,去除冗余空格和换行符
    cleaned_html = re.sub(r'\s+', ' ', str(soup).replace("\n", "")).strip()

    _messages = [
        {"role": "system",
         "content": "You are an expert at analyzing the structure of application forms and filling instructions from HTML content."},
        {"role": "user", "content": f'''Your HTML content is:\n{cleaned_html}'''}
    ]

    # 将HTML转换为JSON
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=_messages,
        functions=[
            {
                "name": "parse_fill_elements",
                "description": "Parse all fill elements in HTML and extract filling details.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "Tag": {"type": "string",
                                            "description": "The tag of the element (e.g., input, select, textarea)."},
                                    "Type": {"type": "string",
                                             "description": "The type attribute of the element if applicable."},
                                    "Name": {"type": "string",
                                             "description": "The name attribute of the element."},
                                    "Id": {"type": "string", "description": "The id attribute of the element."},
                                    "Label": {"type": "string",
                                              "description": "The label and information which can associate with the fill element. If the element is a checkbox or radio button, the 'Label' attribute will include the question message and its text. Don't worry about the question getting too long, just put it in its entirety and in front of the main answer (not for Children). Be sure to remove newline characters and redundant spaces."},
                                    'Children': {"type": "array",
                                                 "description": "A list of child elements which has the same structure and properties as items. If an element has logic that affects other elements, such as checkboxes enabling or showing other input fields, the affected elements will be listed here.",
                                                 "items": {
                                                     "type": "object",
                                                     "properties": {
                                                         "Tag": {"type": "string"},
                                                         "Type": {"type": "string"},
                                                         "Name": {"type": "string"},
                                                         "Id": {"type": "string"},
                                                         "Label": {"type": "string"},
                                                         "Child": {
                                                             "type": "array",
                                                             "items": {}
                                                         }
                                                     },
                                                     "required": ["Tag", "Id", "Label", "Children"]
                                                 }
                                                 },
                                },
                                "required": ["Tag", "Id", "Label", "Children"]
                            }
                        }
                    },
                    "required": ["data"]
                }
            }
        ],
        stream=True,  # 使用流式输出避免输出内容截断
        function_call={
            "name": "parse_fill_elements"
        },
    )
    result = ""
    for chunk in completion:
        if chunk.choices[0].delta.function_call:
            result += chunk.choices[0].delta.function_call.arguments

    output_tokens = len(encoding.encode(result))
    input_tokens = sum(len(encoding.encode(msg['content'])) for msg in _messages)
    print("输入token数:", input_tokens)
    print("输出token数:", output_tokens)
    print("总token数:", input_tokens + output_tokens)
    with open('result/yale_stream_result.json', 'w', encoding='utf-8') as f:
        f.write(result)


if __name__ == '__main__':
    AI_parser(local_html)
