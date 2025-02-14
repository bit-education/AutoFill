import json
from openai import OpenAI

AI_MATCH_CONTEXT = "You are a data processing expert who can match the html elements with keys of the student information and add the key into the corresponding element."

def match_keys(
    api_key: str,
    frontend_fields: list[dict], 
    database_fields: dict,
    model: str = "gpt-4o-mini",
):
    client = OpenAI(api_key=api_key)
    matching_prompt = f"""
        Here is the student data dictionary:
        {database_fields}
        HTML elements:
        {frontend_fields}
    """
    _messages = [
        {
            "role": "system",
            "content": AI_MATCH_CONTEXT},
        {
            "role": "user",
            "content": matching_prompt}
    ]
    
    completion = client.chat.completions.create(
        model=model,
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
                                    "Tag": {"type": "string", "description": "The tag attribute of the element(include children's elements)."},
                                    "Id": {"type": "string", "description": "The id attribute of the element(include children's elements)."},
                                    "Label": {"type": "string", "description": "The label attribute of the element(include children's elements)."},
                                    "Key": {"type": "string",
                                            "description": "The key of the student data dictionary which can match the meaning with the element's label. Note that label is preferred for matching and the value of student dictionary should not be used to match. If the id, name, and class attributes are also related, they can be combined with the meaning of the label to match. If no direct match exists for the element, use the most possibly fitting key. Key attribute should not be empty."},
                                },
                                "description": "The element of matching result which has been added key attribute.",
                            },
                            "required": ["Key"]
                        }
                    },
                }
            }
        ],
        function_call={
            "name": "match_entries"
        },
    )
    
    ans = completion.choices[0].message.function_call.arguments
    return json.loads(ans)['result']