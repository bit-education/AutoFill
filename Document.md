# Document

<img src=".\pictures\extension.png" alt="extension" style="zoom: 80%;" />

## 后端

1. **app.py**

   利用Flask搭建了后端接口与前端进行数据通信，包括：

   ① `url`端口：

   与前端交互URL的缓存信息，并将缓存信息储存在`Hash_name.json`中。

   ② `submit`端口：

   Ⅰ 验证管理员密码和学生ID，验证通过后再对学校申请页面是否有缓存进行验证，分两种情况：

   - 若该申请页面没有缓存，则对该页面进行AI解析和匹配，将对应申请页面和学生ID缓存到`Name_cache.json`中。

   - 若该申请页面已经缓存过，但是学生ID为缓存到对应的申请页面中，则将该学生ID放到对应的申请页面中并缓存到`Name_cache.json`中。

   Ⅱ 利用AI解析的结果，调用填充函数获取需要填充的id和学生信息，并将其传回前端进行填回操作。

   ③ `mappings`端口：

   根据缓存方案二，更新并缓存用户修改的数据映射字段。

2. **functions.py**

   重写AI解析和匹配中的`AI_parser`、`html_parser`和`Match`函数，修改其数据的返回结构，更加适应前后端交互操作。

3. **Fill.py**（返回填充框和数据的匹配关系）

   实现学生数据和申请页面的匹配，根据已知的填充标签，分四种情况进行匹配：

   - `input`标签：直接用id与其对应文本进行匹配。

   - `textarea`标签：同`input`标签。

   - `select`标签：利用轻量BERT得到学生数据与对应`select`标签下的所有`option`选项得余弦相似度，选择最相似的`option`选项与`select`的id进行匹配。

   - `checkbox`标签与`radio`标签：

     `radio`（单选）：操作与`select`类似，直接获取最高相似度的`radio id`。

     `checkbox`（多选）：同样获取学生数据与所有`checkbox`的余弦相似度，选定相对阈值分位数，选择高于阈值的`checkbox id`。

4. **AI_parser.py/html_parser.py/AI_match.py**

   实现AI解析、BS解析和AI匹配的基本功能。

5. **extract_data.py**

   获取学生数据库的数据。



## 前端

**scripts/popup.js**

- `highlightFields`函数：高亮已解析的填充框。

- `fill`函数：根据后端传回的填充框和数据的匹配关系，利用原生java script进行学生数据填回。

- `clearAllFields`函数：清空html中已填充内容。

- `generateHash`函数：生成当前申请页面URL的hash ID值。

- 按钮操作：

  ① `submitButton`：对应Submit按钮，在用户填写了对应学生ID和管理员密码后提交当前页面的信息给后端submit端口，并获取后端处理完毕的数据进行学生数据填回。

  ② `clearButton`：对应Clear按钮，清空用户在插件上填写的信息。

  ③`mappingButton`：对应插件最下方的Submit Mappings按钮，提交用户手动修改的匹配信息，将用户新修改的匹配关系缓存到后端`results/{hash ID}_result.json`中。

