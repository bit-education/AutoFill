import requests

def parse_type(content):
    tp = content["type"]
    if tp == "text":
        return content["text"]["content"]
    elif tp == "number":
        return content["number"]
    elif tp == "rich_text":
        if len(content["rich_text"]) > 0:
            return parse_type(content["rich_text"][0])
        else:
            return ""
    elif tp == "title":
        if len(content["title"]) > 0:
            return parse_type(content["title"][0])
        else:
            return ""
    elif tp == "people":
        return (content["people"][0]["name"], content["people"][0]["id"])
    elif tp == "phone_number":
        return content["phone_number"]
    elif tp == "email":
        return content["email"]
    elif tp == "date":
        date = content['date']
        if not isinstance(date, dict):
            return ""
        if date["start"] and date["end"]:
            return f"{date['start']} - {date['end']}"
        elif date["start"]:
            return date["start"]
        elif date["end"]:
            return date["end"]
        else:
            return ""
    elif tp == "status":
        return content["status"]['name']
    elif tp == "relation":
        return [relation["id"] for relation in content["relation"]]
    elif tp == "select":
        if content["select"]:
            return content["select"]['name']
        else:
            return ""
    else:
        raise NotImplementedError(f"Can't recognize type {tp}")
    
def db_get_table(
    notion_secret_key: str,
    database_id: str,
) -> dict:
    headers = {
        "Authorization": f"Bearer {notion_secret_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    response = requests.post(url, headers=headers)
    results = response.json()["results"]
    table = {}
    for result in results:
        page_id = result["id"]
        properties = result["properties"]
        extracted_props = {}
        for key in properties:
            extracted_props[key] = parse_type(properties[key])
        table[page_id] = extracted_props
    return table

def db_get_page_by_id(
    notion_secret_key: str,
    page_id: str,
) -> dict:
    headers = {
        "Authorization": f"Bearer {notion_secret_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    url = f"https://api.notion.com/v1/pages/{page_id}"
    response = requests.get(url, headers=headers)
    
    properties = response.json()["properties"]
    extracted_props = {}
    for key in properties:
        extracted_props[key] = parse_type(properties[key])
    
    return extracted_props

if __name__ == "__main__":
    # table = db_get_table(
    #     notion_secret_key="secret_w5c6OW83vfIGJYSjMCZPYtI34RaZa47H2lou0Iqd9aG",
    #     database_id="16bc92c3d49180fbb257cb4379831816"
    # )
    # print(table)
    
    print(db_get_page_by_id(
        notion_secret_key="secret_w5c6OW83vfIGJYSjMCZPYtI34RaZa47H2lou0Iqd9aG",
        page_id="16bc92c3-d491-8082-8da6-d6d10417d1ad",
    ))
    