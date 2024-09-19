"""
AI匹配数据库条目与html对应label，并将匹配的条目放入对应html元素中
"""
import json
import tiktoken
import copy
from openai import OpenAI

test_U = "nyu"
encoding = tiktoken.encoding_for_model("gpt-4")


def AI_match(elements, database):
    API_KEY = open('../API_KEY.txt', 'r').read()
    client = OpenAI(api_key=API_KEY)

    matching_prompt = f"""
        Here is the student data dictionary:
        {database}
        HTML elements:
        {elements}
    """
    _messages = [
        {
            "role": "system",
            "content": "You are a data processing expert who can match the html elements with the student information and add the key into the corresponding element."},
        {
            "role": "user",
            "content": matching_prompt}
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=_messages,
        functions=[
            {
                "name": "match_entries",
                "description": "Match database entries and its meaning with HTML content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "result": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "Tag": {"type": "string", "description": "The tag attribute of the element."},
                                    "Id": {"type": "string", "description": "The id attribute of the element."},
                                    "Label": {"type": "string", "description": "The label attribute of the element."},
                                    "Key": {"type": "string",
                                            "description": "The key of the student data dictionary which can match the meaning with the element's label. Note that label is preferred for matching. If the id, name, and class attributes are also related, they can be combined with the meaning of the label to match. If no direct match exists for the element, use the most possibly fitting key."},
                                },
                                "description": "The element of matching result which has been added key attribute.",
                            },
                            "required": ["Tag", "Id", "Key"]
                        }
                    },
                }
            }
        ],
        function_call={
            "name": "match_entries"
        },
    )
    result = completion.choices[0].message.function_call.arguments
    output_tokens = len(encoding.encode(result))
    input_tokens = sum(len(encoding.encode(msg['content'])) for msg in _messages)
    print("输入token数:", input_tokens)
    print("输出token数:", output_tokens)
    print("总token数:", input_tokens + output_tokens)
    return json.loads(result)['result']


# 处理测试用例
def read_Utest_json():
    Utest_json = json.load(open(f'../result/final/{test_U}_final_result.json', 'r', encoding='utf-8'))
    unnecessary_key = ['Type', 'Required', 'Children', 'Options', 'Disabled']
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


# 测试用例
def test():
    data = json.load(open('./data/Student_data.json', 'r', encoding='utf-8'))
    Utest = read_Utest_json()
    results = AI_match(Utest, data[-1])
    with open(f'./results/{test_U}_result.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    test()
