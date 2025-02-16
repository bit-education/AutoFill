import React from 'react';
import ReactDOM from 'react-dom';
import { Select } from 'antd';

const ip = "http://127.0.0.1:5000/"

function highlightFields(fields) {
    fields.forEach(field => {
        const element = document.getElementById(field.Id);
        if (element) {
            element.style.border = '2px solid green';
            element.style.backgroundColor = '#ffe6e6';
            element.title = `Label: ${field.Label}, ID: ${field.Id}`;
        } else {
            console.warn(`Element not found for ID: ${field.Id}`);
        }
    });
}

// js填回html
function fill(fill_set) {
    // 填input和textarea
    const input_field = fill_set["input"];
    for (let id in input_field) {
        const inputElement = document.getElementById(id);
        if(inputElement && inputElement.tagName === 'INPUT' && inputElement.type === 'text') {
            inputElement.value = input_field[id];
            const event = new Event('input', { bubbles: true });
            inputElement.dispatchEvent(event);
        }
    }
    // 填checkbox和radio
    const cr_field = fill_set["checkbox_radio"];
    cr_field.forEach((id) => {
        const crElement = document.getElementById(id);
        if(crElement) {
            crElement.checked = true;
            const event = new Event('change', { bubbles: true });
            crElement.dispatchEvent(event);
        }
    });
    // 填select
    const select_field = fill_set["select"];
    for (let id in select_field) {
        let value = select_field[id];
        const selectElement = document.getElementById(id);
        if(selectElement) {
            // 处理没有value属性的情况
            const optionFound = Array.from(selectElement.options).some(option => {
                if ((option.value && option.value === value) || (!option.value && option.text === value)) {
                    option.selected = true;
                    const event = new Event('change', { bubbles: true });
                    selectElement.dispatchEvent(event);
                    return true;
                }
                return false;
            });
            if (!optionFound) {
                console.warn(`Option with value "${value}" not found in select element "${id}"`);
            }
        }
    }
}

// 清空html中已填充内容
function clearAllFields() {
    // 清空所有input元素
    document.querySelectorAll('input').forEach(input => {
        if (input.type === 'checkbox' || input.type === 'radio') {
            input.checked = false;
        } else {
            input.value = '';
        }
    });

    // 清空所有textarea元素
    document.querySelectorAll('textarea').forEach(textarea => {
        textarea.value = '';
    });

    // 清空所有select元素
    document.querySelectorAll('option').forEach(select => {
        option.selected = false;
    });
}


function generateHash(input) {
    let hash = 0, i, chr;
    for (i = 0; i < input.length; i++) {
        chr = input.charCodeAt(i);
        hash = ((hash << 5) - hash) + chr;
        hash |= 0; // Convert to 32bit integer
    }
    return hash.toString();
}

document.addEventListener("DOMContentLoaded", function() {
    const submitButton = document.getElementById("submit_btn");
    const clearButton = document.getElementById("clear_btn");
    const mappingsButton = document.getElementById("mappingsBtn");
    const loader = document.getElementById("loader");
    const studentId = document.getElementById("id");
    const password = document.getElementById("password");
    const selections = {};
    const handleChange = (id, values) => {
        selections[id] = values;
    };
    var identifier;
    if(submitButton){
        submitButton.addEventListener("click", async function() {
            if (!studentId.value || studentId.value === "") {
                alert("Student's id can't be empty!");
            }
            if (!password.value || password.value === "") {
                alert("Password can't be empty!");
            }

            // 禁用按钮和输入框，防止用户修改或者重复点击提交
            submitButton.disabled = true;
            clearButton.disabled = true;

            // 显示加载动画
            loader.style.display = "block";

            studentId.disabled = true;
            password.disabled = true;

            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            // 获取当前页面的URL
            const url = new URL(tab.url);
            const path = url.pathname;
            // 提取当前url的信息
            let url_name = url.hostname + path + url.search;
            url_name = url_name.replace(/[/.?]/g, "_");
            identifier = generateHash(`_${url_name}_`);
            console.log('当前页面的唯一标识符:' + identifier + "\n" + url_name);
            try {
                // 将url缓存发送到后端
                const response = await fetch(ip + "url", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        name: url_name,
                        hash_id: identifier
                    }),
                });
            } catch(error) {
                console.error('Error:', error);
                alert("An error occurred while communicating with the server.");
            } finally {
                document.getElementById("url").innerText = identifier + " : " + url_name;
            }
            // 获取当前网页的 HTML 源码
            chrome.scripting.executeScript(
                {
                    target: { tabId: tab.id },
                    func: () => document.documentElement.outerHTML, // 获取 HTML 源码
                },
                async (results) => {
                    const htmlSource = results[0].result;

                    try{
                        // 将数据发送到后端
                        const response = await fetch(ip + "submit", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                            },
                            body: JSON.stringify({
                                name: identifier,
                                student_id: studentId.value,
                                password: password.value,
                                html_source: htmlSource
                            }),
                        });

                        const result = await response.json();
                        if (result.error) {
                            document.getElementById("message").innerText = result.error;
                        } else {
                            chrome.scripting.executeScript({
                                target: { tabId: tab.id },
                                func: clearAllFields
                            });
                            /* 法一:替换HTML源码(会有闪烁或者元素隔开现象)
                            // 替换当前网页内容为填充后的 HTML
                            chrome.scripting.executeScript({
                                target: { tabId: tab.id },
                                func: (html) => { document.documentElement.innerHTML = html; },
                                args: [result.filled_html]
                            });*/

                            // 法二:获取HTML需要填充的id和信息传回js操作
                            chrome.scripting.executeScript({
                                target: { tabId: tab.id },
                                func: fill,
                                args: [result.filled_set]
                            });

                            document.getElementById("message").innerText = "Form successfully filled!";
                        }
                        const parsedFields = result.parsed_fields;

                        // 在前端高亮需要映射的表单元素
                        chrome.scripting.executeScript({
                            target: { tabId: tab.id },
                            func: highlightFields,
                            args: [parsedFields]
                        });
                        // 显示解析结果
                        const parsed_field = document.getElementById("parsed_field");
                        parsed_field.style.display = "";
                        const mappingForm = document.getElementById("mappingForm");
                        mappingForm.innerHTML = "";  // 清空之前的内容
                        // 设置多选选项
                        const options = result.students_fields;

                        const MultiSelect = ({ id, onChange, defaultTags }) => (
                            <Select
                                mode="tags"
                                style={{
                                  width: '100%',
                                }}
                                placeholder="Database Fields"
                                onChange={values => onChange(id, values)}
                                defaultValue={defaultTags}
                                options={options}
                            />
                        );
                        parsedFields.forEach(field => {
                            // 创建 label 和 div 块
                            const label = document.createElement('label');
                            label.setAttribute("for", field.Id);
                            label.textContent = `Label: ${field.Label}, ID: ${field.Id}`;

                            const div = document.createElement('div');
                            div.setAttribute("id", field.Id);
                            let selected_options = [];
                            if(field.Key instanceof Array){
                                selected_options = field.Key;
                            }
                            else{
                                selected_options.push(field.Key);
                            }
                            mappingForm.appendChild(label);
                            mappingForm.appendChild(div);
                            mappingForm.appendChild(document.createElement('br'));
                            // 添加MultiSelect组件
                            ReactDOM.render(<MultiSelect id={field.Id} onChange={handleChange} defaultTags={selected_options} />, document.getElementById(field.Id));
                        });
                    } catch (error) {
                        console.error('Error:', error);
                        alert("An error occurred while communicating with the server.");
                    } finally {
                        // 恢复按钮状态
                        submitButton.disabled = false;
                        clearButton.disabled = false;
                        studentId.disabled = false;

                        //password.value = "";
                        loader.style.display = "none";
                    }
                }
            );
        });
    }

    if(clearButton){
        clearButton.addEventListener("click", function() {
            password.disabled = false;
            studentId.value = "";
            password.value = "";
            document.getElementById("message").innerText = "";
        });
    }

    if(mappingsButton){
        mappingsButton.addEventListener("click", async function() {
            if(!identifier) {
                alert('An error occurred: identifier not found!');
            }
            // 提交字段映射到后端
            const response = await fetch(ip + "mappings", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: identifier,
                    mappings: selections,
                }),
            });
            const result = await response.json();
            alert(result.message);
            // 回到顶部
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }
});

