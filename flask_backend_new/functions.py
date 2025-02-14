
# parser
from autofill.parser.html.ai_parser import AIHTMLParser
from autofill.parser.html.bs_parser import load_html_as_bs, bs_parse_tag_input, bs_parse_tag_select, bs_parse_tag_label, bs_parse_tag_textarea, bs_html_clean, clean_html_str

# match
from autofill.matching.ai_match import match_keys
from autofill.matching.database import db_get_table, db_get_page_by_id

# fill
from autofill.fill.html_fill import BS_fill_js

def parse_html(
    html:str, 
    ai_api_key:str,
    is_file:bool=False,
) -> dict:
    # bs parsing
    bs = load_html_as_bs(html=html, isfile=is_file)
    input_fields = bs_parse_tag_input(bs)
    select_fields = bs_parse_tag_select(bs)
    textarea_fields = bs_parse_tag_textarea(bs)
    bs_parse_out = {
        'input': input_fields,
        'select': select_fields,
        'textarea': textarea_fields,
    }
    
    # TODO: it's extremely slow for the ai parsing
    # ai parsing
    ai_parser = AIHTMLParser(
        api_key=ai_api_key,
        model="gpt-4o"
    )
    html_cleaned = bs_html_clean(bs, save_options=3)
    html_cleaned = clean_html_str(html_cleaned)
    ai_parse_ = ai_parser.parse_html(
        html=html_cleaned,
        chunk_mode="text",
        chunk_size=16384,
        chunk_overlap=2000
    )
    ai_parse_out = {'input': [], 'select': [], 'textarea': []}

    # search tags 'input', 'select', and 'textarea' in ai results
    def find_field_all_result(field):
        if 'Children' not in field or len(field['Children']) == 0:
            if field['Tag'] == 'input':
                ai_parse_out['input'].append(field)
                return
            elif field['Tag'] == 'select' or field['Tag'] == 'datalist':
                # 将在Children中的options删除
                field['Children'] = []
                ai_parse_out['select'].append(field)
                return
            elif field['Tag'] == 'textarea':
                ai_parse_out['textarea'].append(field)
                return
        else:
            for child in field['Children']:
                find_field_all_result(child)

    for ai_result in ai_parse_:
        find_field_all_result(ai_result)
        
    # match label info in ai parsing with bs parsing
    for input_field in bs_parse_out['input']:
        for ai_field in ai_parse_out['input']:
            if input_field['Id'] == ai_field['Id']:
                input_field['Label'] = ai_field['Label']
                break

    for select_field in bs_parse_out['select']:
        for ai_field in ai_parse_out['select']:
            if 'Id' in select_field and 'Id' in ai_field:
                if select_field['Id'] == ai_field['Id']:
                    select_field['Label'] = ai_field['Label']
                    break
            elif 'Name' in select_field and 'Name' in ai_field:
                if select_field['Name'] == ai_field['Name']:
                    select_field['Label'] = ai_field['Label']
                    break

    for textarea_field in bs_parse_out['textarea']:
        for ai_field in ai_parse_out['textarea']:
            if textarea_field['Id'] == ai_field['Id'] and ai_field['Tag'] == 'textarea':
                textarea_field['Label'] = ai_field['Label']
                break

    no_label_set = []

    # removing elements with no labels matched
    def remove_no_label_field(field_list: list[dict]):
        result = []
        for field in field_list:
            if field.get('Label') or field.get('Options'):
                result.append(field)
            else:
                no_label_set.append(field)
        return result
    
    bs_parse_out['input'] = remove_no_label_field(bs_parse_out['input'])
    bs_parse_out['select'] = remove_no_label_field(bs_parse_out['select'])
    bs_parse_out['textarea'] = remove_no_label_field(bs_parse_out['textarea'])
    
    return bs_parse_out

def match(
    student_id: str,
    parse_result: dict,
    ai_api_key:str,
    db_api_key:str,
):
    # remove unnecessary keys:
    unnecessary_key = ['Type', 'Required', 'Options', 'Disabled']
    source_data = []
    for input_field in parse_result['input']:
        for key in unnecessary_key:
            if key in input_field:
                input_field.pop(key)
        source_data.append(input_field)
    for select_field in parse_result['select']:
        for key in unnecessary_key:
            if key in select_field:
                select_field.pop(key)
        source_data.append(select_field)
    for textarea_field in parse_result['textarea']:
        for key in unnecessary_key:
            if key in textarea_field:
                textarea_field.pop(key)
        source_data.append(textarea_field)
    # get student data
    student_data = db_get_page_by_id(
        notion_secret_key=db_api_key,
        page_id=student_id
    )
    # match
    matches = match_keys(
        api_key=ai_api_key,
        frontend_fields=source_data,
        database_fields=student_data,
        model="gpt-4o"
    )
    return matches, student_data