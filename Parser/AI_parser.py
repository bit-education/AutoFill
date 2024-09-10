import json
import re
from openai import OpenAI
from bs4 import BeautifulSoup

headers = {"Content-Type": "application/json"}
local_html = open('test_data/usc_test.html', 'r', encoding='utf-8').read()
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

    # 将options删除到至多3个
    for select in soup.find_all(['select', 'datalist']):
        options = select.find_all('option')
        if len(options) > 3:
            for option in options[3:]:
                option.decompose()

    soup = soup.prettify()
    # 获取精简后的HTML,去除冗余空格和换行符
    cleaned_html = re.sub(r'\s+', ' ', str(soup).replace("\n", "")).strip()

    # with open('yale_cleaned.html', 'w', encoding='utf-8') as f:
    #     f.write(cleaned_html)
    # 将HTML转换为JSON
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system",
             "content": "You are an expert at analyzing the structure of application forms and filling instructions from HTML content."},
            {"role": "user", "content": cleaned_html}
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "parse_fill_elements",
                    "description": "Parse fill elements from HTML and extract filling details.",
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
                                                  "description": "Summary of the label and other simple description which can associate with the element. If an element is a checkbox or radio button, the label will be question information and its text. Be sure to remove newline characters and redundant spaces."},
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
                                                      "required": ["Tag", "Type", "Id", "Label", "Children"]
                                                  }
                                                  },
                                    },
                                    "required": ["Tag", "Type", "Id", "Label", "Children"]
                                }
                            }
                        },
                        "required": ["data"]
                    }
                }
            }
        ],
        tool_choice={
            "type": "function",
            "function": {"name": "parse_fill_elements"}
        },
        # stream=True,
    )

    result = completion.choices[0].message.tool_calls[0].function.arguments
    # result = ""
    # for chunk in completion:
    #     if chunk.choices[0].delta.content is not None:
    #         result += chunk.choices[0].delta.content
    # print(result)
    with open('result/usc_result.json', 'w', encoding='utf-8') as f:
        f.write(result)


if __name__ == '__main__':
    AI_parser(local_html)
