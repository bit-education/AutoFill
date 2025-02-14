from pathlib import Path
import json
import copy
from flask import Flask, request, jsonify
from functions import parse_html, match, BS_fill_js

app = Flask(__name__)
working_dir = Path(__file__).parent
CONFIG = json.load(open(working_dir / "config.json", "r", encoding="utf-8"))


# 执行学生数据匹配主函数
def main(html: str, student_id: str):
    # 前端解析与AI labeling
    parse_res = parse_html(html=html, ai_api_key=CONFIG["ai_api_key"], is_file=False)
    parse_out = copy.deepcopy(parse_res)
    # 数据库字段与前端匹配
    matches, db_data = match(student_id=student_id, parse_result=parse_res, ai_api_key=CONFIG["ai_api_key"], db_api_key=CONFIG["db_api_key"])
    return matches, parse_out, db_data

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