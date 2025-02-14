import re
from typing import List
from bs4 import BeautifulSoup

BS_UNRELAVENT_TAGS = ['a', 'head', 'script', 'style', 'img', 'link', 'meta', 'footer', 'nav', 'hr', 'meter', 'object',
                    'noscript', 'video', 'canvas', 'picture', 'header', 'font', 'button']
BS_SAVE_ATTRS = ['class', 'id', 'name', 'type', 'for', 'value', 'title', 'alt', 'onchange', 'onclick', 'data-text', 'data-type', 'required', 'label', 'selected']

def load_html_as_bs(html:str, isfile:bool=True) -> BeautifulSoup:
    """load an html string or file path as a beautiful soup class

    Args:
        html (str): html string or file path
        isfile (bool, optional): Set to True if 'html' is a file. Defaults to True.

    Returns:
        BeautifulSoup: A beautiful soup class that wraps the html content
    """
    if isfile:
        assert html.endswith(".html"), f"[Error][bs parser] {html} is not a legal html filepath! Set isfile to False if it is a html string"
        with open(html, 'r', encoding='utf-8') as f:
            html_content:str = f.read()
    else:
        html_content = str(html)
    bs = BeautifulSoup(
        markup=html_content,
        features="html.parser"
    )
    return bs

def bs_parse_tag_input(bs: BeautifulSoup) -> List[dict]:
    """parse elements with tag 'input' into list of dict"""
    input_fields = []
    for input_field in bs.find_all('input'):
        input_fields.append({
            'Tag': input_field.name,
            'Name': input_field.get('name'),
            'Id': input_field.get('id'),
            'Type': input_field.get('type'),
            'Required': input_field.get('required'),
            'Children': []
        })
    return input_fields

def bs_parse_tag_select(bs: BeautifulSoup) -> List[dict]:
    """parse elements with tag 'select' into list of dict"""
    select_fields = []
    for select_field in bs.find_all(['select', 'datalist']):
        options = select_field.find_all('option')
        options = [option for option in options if not option.text.strip()=='']
        if len(options) > 0:
            select_fields.append({
                'Tag': select_field.name,
                'Name': select_field.get('name'),
                'Id': select_field.get('id'),
                'Class': select_field.get('class'),
                'Disabled': select_field.get('disabled'),
                'Options': {
                    'Value': [option.get('value') for option in options],
                    'Text': [re.sub(r'\s+', ' ', option.text).strip() for option in options],
                },
                'Required': select_field.get('required'),
                'Children': []
            })
    return select_fields

def bs_parse_tag_textarea(bs: BeautifulSoup) -> List[dict]:
    """parse elements with tag 'textarea' into list of dict"""
    textarea_fields = []
    for textarea_field in bs.find_all('textarea'):
        textarea_fields.append({
            'Tag': textarea_field.name,
            'Name': textarea_field.get('name'),
            'Id': textarea_field.get('id'),
            'Required': textarea_field.get('required'),
            'Children': []
        })

    return textarea_fields

def bs_parse_tag_label(bs: BeautifulSoup) -> List[dict]:
    """parse elements with tag 'label' into list of dict"""
    label_fields = []
    for label_field in bs.find_all('label'):
        label_fields.append({
            'Tag': label_field.name,
            'Name': label_field.get('name'),
            'Id': label_field.get('id'),
            'Class': label_field.get('class'),
            'Required': label_field.get('required'),
            'For': label_field.get('for'),
            'Value': str(label_field.text).strip(),
        })

    return label_fields

def bs_html_clean(
    bs: BeautifulSoup,
    remove_tags: List[str] = BS_UNRELAVENT_TAGS,
    save_attrs: List[str] = BS_SAVE_ATTRS,
    save_options: int = -1,
) -> str:
    # remove unrelavent tags
    if len(remove_tags) > 0:
        for tag in bs(remove_tags):
            tag.decompose()
    # remove large quantity options
    if save_options >= 0: # set -1 for not removing any options
        for select in bs.find_all(['select', 'datalist']):
            options = select.find_all('option')
            if len(options) > save_options:
                for option in options[save_options:]:
                    option.decompose()
    # remove unimportant attrs
    if len(save_attrs) > 0:
        for tag in bs.find_all(True):
            if tag.attrs:
                tag.attrs = {k: v for k, v in tag.attrs.items() if k in save_attrs}
    bs = bs.prettify()
    return bs

def clean_html_str(html: str) -> str:
    # remove space and return characters
    cleaned_html = re.sub(r'\s+', ' ', str(html).replace("\n", "")).strip()
    # remove comments in html
    cleaned_html = re.sub(r'<!--.*?-->', '', cleaned_html, flags=re.DOTALL)
    return cleaned_html

if __name__ == "__main__":
    bs = load_html_as_bs(
        html="UW.html",
        isfile=True
    )
    # print(bs_parse_tag_input(bs))
    # print(bs_parse_tag_select(bs))
    # print(bs_parse_tag_textarea(bs))
    # print(bs_parse_tag_label(bs))
    bs = bs_html_clean(bs, save_options=3)
    # print(bs)
    # print(clean_html_str(str(bs)))
    
    html = clean_html_str(str(bs))
    
    print(html)
    
    # from html_chunking import get_html_chunks
    
    # html_chunks = get_html_chunks(
    #     html,
    #     max_tokens=4000,
    #     is_clean_html=True, 
    #     attr_cutoff_len=25
    # )
    
    # print(len(html_chunks))
    # # for i in html_chunks:
    # #     print(i)
    # #     print("\n\n")