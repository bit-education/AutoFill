import json
import time
from flask import Flask, request, jsonify
from Fill import BS_fill_js
from functions import AI_parser, html_parser, Match

app = Flask(__name__)
PASSWORD = "123456"
TEST = False
# 学生申请学校的缓存,格式为{hash ID: 学生ID}
U_Cache = json.load(open("./data/Name_cache.json", "r", encoding="utf-8"))
# 学生数据库的学生信息
students = json.load(open("./data/Student_data.json", "r", encoding="utf-8"))


# 提取后端数据库字段供前端选择
def get_fields():
    fields = []
    for column in students[0].keys():
        fields.append({'value': column, 'label': column})
    return fields


# 根据ID查找对应学生信息
def find_student_by_id(student_id):
    for student in students:
        if student["ID"] == student_id:
            return student
    return None


# 执行学生数据匹配主函数
def main(html_source, name):
    # AI解析
    AI_parser(html_source, name)
    # 利用AI解析的结果和bs解析的结果,匹配生成最终解析结果
    html_parser(html_source, name)
    # AI匹配
    Match(name)


@app.route('/url', methods=['POST', "GET"])
def url():
    # 保存大学申请网页对应的hash ID,格式为{hash ID: 学校申请页面的url}
    hash_name = json.load(open("./data/Hash_name.json", "r", encoding="utf-8"))
    if request.method == 'POST':
        data = request.json
        url_name = data.get('name')
        identifier = data.get('hash_id')
        if identifier not in hash_name.keys():
            hash_name[identifier] = url_name
            json.dump(hash_name, open("./data/Hash_name.json", "w", encoding="utf-8"), indent=4)
            return jsonify({"message": "success"}), 200
        else:
            return jsonify({"message": "exist"}), 200


@app.route('/submit', methods=['POST'])
def submit():
    s = time.time()
    if TEST:
        # 使用postman测试接口
        print(request.files)
        print(request.form)
        data = request.form
        name = data.get('name')
        student_id = data.get('student_id')
        password = data.get('password')
        html_source = request.files['html_source'].read().decode('utf-8')
    else:
        data = request.json
        name = data.get('name')  # 申请页面的hash ID
        student_id = data.get('student_id')  # 学生ID
        password = data.get('password')  # 管理员密码
        html_source = data.get('html_source')  # 学生申请页面的html源码
    # 验证管理员密码
    if password != PASSWORD:
        return jsonify({"error": "Invalid password"}), 403
    # 查找学生信息
    student_data = find_student_by_id(student_id)
    if not student_data:
        return jsonify({"error": "Student not found"}), 404

    # 验证name是否存在或者已经缓存过，若有缓存，直接使用缓存进行填回；否则需要解析匹配
    if name not in U_Cache:  # 如果该申请页面没有缓存
        main(html_source, name)
        U_Cache[name] = [student_id]
        json.dump(U_Cache, open("./data/Name_cache.json", "w", encoding="utf-8"), indent=4)
    else:
        if student_id not in U_Cache[name]:  # 如果该学生尚未填过，但已有申请页面缓存
            U_Cache[name].append(student_id)
            json.dump(U_Cache, open("./data/Name_cache.json", "w", encoding="utf-8"), indent=4)

    parse_result = json.load(open(f"./results/{name}_result.json", "r", encoding="utf-8"))

    # # 法一:替换HTML源码(会有闪烁或者元素隔开现象)
    # BS = BS_fill(test_result, html_source, student_data, name)
    # filled_html = BS.Fill()

    # 法二:获取HTML需要填充的id和信息传回js操作
    BS_js = BS_fill_js(parse_result, html_source, student_data, name)
    fill_set = BS_js.Fill()

    print("解析匹配总时间: %4f s" % (time.time() - s))
    students_fields = get_fields()
    return jsonify({"filled_set": fill_set, "parsed_fields": parse_result, "students_fields": students_fields})


# 缓存方案2：更新字段映射
@app.route('/mappings', methods=['POST'])
def mappings():
    data = request.json
    name = data.get('name')
    mapping = data.get('mappings')
    print(mapping)
    # 更新字段映射
    test_result = json.load(open(f"./results/{name}_result.json", "r", encoding="utf-8"))
    for Id, Key in mapping.items():
        if Key is not []:
            for field in test_result:
                if field["Id"] == Id:
                    field["Key"] = Key
                    break

    json.dump(test_result, open(f"./results/{name}_result.json", "w", encoding="utf-8"), indent=4)
    return jsonify({"message": "Cache successfully updated"}), 200


if __name__ == '__main__':
    app.run()
