import os
from pathlib import Path
import json
import copy
from flask import Flask, request, jsonify
from functions import parse_html, match, BS_fill_js, db_get_page_by_id

app = Flask(__name__)
working_dir = Path(__file__).parent
CONFIG = json.load(open(working_dir / "config.json", "r", encoding="utf-8"))
URL_HASH_FILE = working_dir / "cache" / "hash_url.json"

# 执行学生数据匹配主函数
def main(html: str, student_id: str):
    # 前端解析与AI labeling
    parse_res = parse_html(html=html, ai_api_key=CONFIG["ai_api_key"], is_file=False)
    parse_out = copy.deepcopy(parse_res)
    # 数据库字段与前端匹配
    matches, db_data = match(student_id=student_id, parse_result=parse_res, ai_api_key=CONFIG["ai_api_key"], db_api_key=CONFIG["db_api_key"])
    return matches, parse_out, db_data

@app.route('/url', methods=['POST', "GET"])
def url():
    # TODO: 未引入多线程保护机制
    # 保存大学申请网页对应的hash ID,格式为{hash ID: 学校申请页面的url}
    hash_name = json.load(open(URL_HASH_FILE, "r", encoding="utf-8"))
    if request.method == 'POST':
        data = request.json
        url_name = data.get('name')
        identifier = data.get('hash_id')
        if identifier not in hash_name.keys():
            hash_name[identifier] = url_name
            json.dump(hash_name, open(URL_HASH_FILE, "w", encoding="utf-8"), indent=4)
            return jsonify({"message": "success"}), 200
        else:
            return jsonify({"message": "exist"}), 200
        
# 缓存方案：更新字段映射
@app.route('/mappings', methods=['POST'])
def mappings():
    data = request.json
    name = data.get('name')
    mapping = data.get('mappings')
    matching_file = working_dir / "cache" / f"cache_{name}" / "match.json"
    # 更新字段映射
    matches = json.load(open(matching_file, "r", encoding="utf-8"))
    for Id, Key in mapping.items():
        if Key is not []:
            for field in matches:
                if field["Id"] == Id:
                    field["Key"] = Key
                    break

    json.dump(matches, open(matching_file, "w", encoding="utf-8"), indent=4)
    return jsonify({"message": "Cache successfully updated"}), 200

@app.route('/submit', methods=['POST'])
def submit():
    data = request.json
    name = data.get('name')  # 申请页面的hash ID
    student_id = data.get('student_id')  # 学生ID
    password = data.get('password')  # 管理员密码
    html_source = data.get('html_source')  # 学生申请页面的html源码
    
    url_hash = json.load(open(URL_HASH_FILE, "r", encoding="utf-8"))
    cache_dir = working_dir / "cache" / f"cache_{name}"
    
    if name in url_hash and cache_dir.exists(): # page has been cached before
        with open(cache_dir / "parse.json", "r") as f:
            parse_res = json.load(f)
        with open(cache_dir / "match.json", "r") as f:
            matches = json.load(f)
        # load student data from db
        db_data = db_get_page_by_id(
            notion_secret_key=CONFIG["db_api_key"],
            page_id=student_id
        )
    else: # page not cached in file
        # create cache dir
        os.makedirs(cache_dir, exist_ok=True)
        # run parsing and matching
        matches, parse_res, db_data = main(
            html=html_source,
            student_id=student_id
        )
        # save files
        with open(cache_dir / "parse.json", "w") as f:
            json.dump(parse_res, f)
        with open(cache_dir / "match.json", "w") as f:
            json.dump(matches, f)
    
    filler = BS_fill_js(
        html=html_source,
        html_parse=parse_res,
        match_result=matches,
        db_data=db_data
    )
    
    fill_set = filler.Fill()

    db_fields = []
    for field in db_fields:
        db_fields.append({
            'value': field,
            'label': field,
        })
    
    return jsonify({"filled_set": fill_set, "parsed_fields": parse_res, "students_fields": db_fields})

def simple_submit():
    test_html_file = "UW.html"
    student_id = "16bc92c3-d491-8082-8da6-d6d10417d1ad"
    with open(test_html_file, 'r', encoding='utf-8') as f:
        html:str = f.read()
        
    # matches, parse_res, db_data = main(
    #     html=html,
    #     student_id=student_id
    # )
    # print("Parse: ", parse_res)
    # print("Match: ", matches)
    
    # with open("parse_out.json", "w") as f:
    #     json.dump(parse_res, f)
    # with open("match_out.json", "w") as f:
    #     json.dump(matches, f)
    # with open("db_data.json", "w") as f:
    #     json.dump(db_data, f)
    
    with open("parse_out.json", "r") as f:
        parse_res = json.load(f)
    with open("match_out.json", "r") as f:
        matches = json.load(f)
    with open("db_data.json", "r") as f:
        db_data = json.load(f)
    
    filler = BS_fill_js(
        html=html,
        html_parse=parse_res,
        match_result=matches,
        db_data=db_data
    )
    fill_set = filler.Fill()
    print(fill_set)


if __name__ == '__main__':
    # app.run()
    simple_submit()