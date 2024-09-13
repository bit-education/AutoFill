import json
import tiktoken
import re
from openai import OpenAI
from bs4 import BeautifulSoup

test_U = "emory"
encoding = tiktoken.encoding_for_model("gpt-4")
headers = {"Content-Type": "application/json"}
local_html = open(f'test_data/{test_U}_test.html', 'r', encoding='utf-8').read()
API_KEY = open('API_KEY.txt', 'r').read()
soup = BeautifulSoup(local_html, 'html.parser')
client = OpenAI(api_key=API_KEY)
unnecessary_tags = ['a', 'head', 'script', 'style', 'img', 'link', 'meta', 'footer', 'nav', 'hr', 'meter', 'object',
                    'noscript', 'video', 'canvas', 'picture', 'header', 'li']


# 将html重叠分块输入到ChatGPT
def chunks_with_overlap(html_text, chunk_size, overlap_size):
    chunks = []
    start = 0
    while start < len(html_text):
        end = min(start + chunk_size, len(html_text))
        chunks.append(html_text[start:end])
        start += (chunk_size - overlap_size)
    return chunks


def generate_messages(chunk, previous_messages=None):
    # 分块输入
    _messages = [
        {"role": "system",
         "content": "You are an expert at parsing the structure of application forms and filling instructions from HTML content. Be careful not to parse the missing elements. Remember the previous extracted information."},
        {"role": "user", "content": f"HTML content is:\n{chunk}"}
    ]
    if previous_messages:
        _messages = [
            {"role": "system",
             "content": "You are an expert at parsing the structure of application forms and filling instructions from HTML content. Be careful not to parse the missing elements. Remember the previous extracted information."},
            {"role": "user",
             "content": f"Previous extracted information:\n{previous_messages}\nHTML content is:\n{chunk}"}
        ]

    # 将HTML转换为JSON
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=_messages,
        functions=[
            {
                "name": "parse_fill_elements",
                "description": "Parse all elements in HTML and extract filling details.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "Tag": {"type": "string",
                                            "description": "The tag of the element (Only contain input, select, textarea and datalist)."},
                                    "Type": {"type": "string",
                                             "description": "The type attribute of the tag if applicable."},
                                    "Name": {"type": "string",
                                             "description": "The name attribute of the tag."},
                                    "Id": {"type": "string",
                                           "description": "The id attribute of the tag."},
                                    "Label": {"type": "string",
                                              "description": "English only. The label and information which can associate with the fill element. If the element is a checkbox or radio button, the 'Label' attribute will include the premise information and its text. If the element is a select element, the 'Label' attribute will include the brief summary of the premise information and its options. Don't worry about the premise information getting too long, just summarize it briefly (don't make it too long) and put it in front of the first answer (not for Children). Be sure to remove newline characters and redundant spaces."},
                                    'Children': {"type": "array",
                                                 "description": "A list of child elements which has the same structure and properties as items. If an element has logic that affects other elements, such as checkboxes enabling or showing other input fields, the affected elements will be listed here. Don't put option tags in here.",
                                                 "items": {
                                                     "type": "object",
                                                     "properties": {
                                                         "Tag": {"type": "string"},
                                                         "Type": {"type": "string"},
                                                         "Name": {"type": "string"},
                                                         "Id": {"type": "string"},
                                                         "Label": {"type": "string"},
                                                         "Children": {
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
        function_call={
            "name": "parse_fill_elements"
        },
        # stream=True
    )
    result = completion.choices[0].message.function_call.arguments
    output_tokens = len(encoding.encode(result))
    input_tokens = sum(len(encoding.encode(msg['content'])) for msg in _messages)

    return result, output_tokens, input_tokens


# 提取上一个回答的最后一个元素作上下文
def extract_relevant_context(message):
    if message and 'data' in message and len(message['data']) > 0:
        return message['data'][-1]
    return None


def AI_parser(html):
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

    with open(f"test_data/cleaned/{test_U}_cleaned.html", "w", encoding="utf-8") as f:
        f.write(cleaned_html)

    chunks = chunks_with_overlap(cleaned_html, 13000, 4000)
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
        json.dump(results, f)


if __name__ == '__main__':
    AI_parser(local_html)
