
# parser
from autofill.parser.html.ai_parser import AIHTMLParser
from autofill.parser.html.bs_parser import load_html_as_bs, bs_parse_tag_input, bs_parse_tag_select, bs_parse_tag_label, bs_parse_tag_textarea, bs_html_clean, clean_html_str

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
    
    print(bs_parse_out)
    
    # ai parsing
    ai_parser = AIHTMLParser(
        api_key=ai_api_key,
        model="gpt-4o-mini"
    )
    html_cleaned = bs_html_clean(bs, save_options=3)
    html_cleaned = clean_html_str(html_cleaned)
    ai_parse_ = ai_parser.parse_html(
        html=html_cleaned,
        chunk_mode="dom",
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
        
    print(ai_parse_out)
        
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