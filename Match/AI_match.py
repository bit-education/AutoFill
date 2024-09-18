"""
AI匹配数据库条目与html内容
"""
import json
import tiktoken
import copy
from openai import OpenAI

encoding = tiktoken.encoding_for_model("gpt-4")


def AI_match(elements, database):
    API_KEY = open('../API_KEY.txt', 'r').read()
    client = OpenAI(api_key=API_KEY)

    matching_prompt = f"""
    You are given a list of HTML elements extracted from a webpage and a dictionary of student information. Your task is:
        1. Match the "Label" attribute of each elements to the corresponding data in the student information dictionary.
        2. Ensure that the values are properly formatted and correctly placed in the HTML input fields.
        3. If an element does not have a direct match, the content most likely to be filled with the "Label" attribute is extracted based on the relevant data. Note that this content must be based on student data.
        4. Return the appropriate "Value" attribute which will be used to insert the student information into the elements.
        Here are the data:
        {database}
        HTML elements:
        {elements}
    """

    _messages = [
        {
            "role": "system",
            "content": "You are an expert at matching dataforms' entries with HTML elements based on the meaning and context. Rely on your human-like understanding to make the best match based on meaning and context. Ensure you do not make obvious mistake in your answer. "},
        {
            "role": "user",
            "content": matching_prompt}
    ]

    completion = client.chat.completions.create(
        model="gpt-4o",
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
                                    "Value": {"type": "string", "description": "The value attribute of the element."},
                                }
                            },
                            "required": ["Tag", "Id", "Label", "Value"]
                        }
                    },
                }
            }
        ],
        function_call="auto",
    )
    result = completion.choices[0].message.function_call.arguments
    output_tokens = len(encoding.encode(result))
    input_tokens = sum(len(encoding.encode(msg['content'])) for msg in _messages)
    print("输入token数:", input_tokens)
    print("输出token数:", output_tokens)
    print("总token数:", input_tokens + output_tokens)
    return json.loads(result)['result']


# 测试用例
def test():
    data = json.load(open('./data/Student_data.json', 'r', encoding='utf-8'))
    Utest_json = json.load(open('../result/final/nyu_final_result.json', 'r', encoding='utf-8'))
    Utest = copy.deepcopy(Utest_json['input'])
    Utest.extend(Utest_json['select'])
    Utest.extend(Utest_json['textarea'])
    results = AI_match(Utest, data[-1])
    with open('result.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    test()
