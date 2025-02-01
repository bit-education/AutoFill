import json
import tiktoken
from typing import Optional, Literal, List
from openai import OpenAI
from html_chunking import get_html_chunks

class AIHTMLParser:
    def __init__(
        self, 
        api_key: str,
        model: str = "gpt-4o"
    ):
        self.agent = OpenAI(api_key=api_key)
        self.model = model
        self.token_counter = tiktoken.encoding_for_model(model)
    
    def get_message(self, chunk_msg: str, prev_msg: Optional[str] = None):
        _messages = [
            {"role": "system",
            "content": "You are an expert at parsing the structure of application forms and filling instructions from HTML content. Be careful not to parse the missing elements. Remember the previous extracted information."},
            {"role": "user", "content": f"HTML content is:\n{chunk_msg}"}
        ]
        if prev_msg:
            _messages = [
                {"role": "system",
                "content": "You are an expert at parsing the structure of application forms and filling instructions from HTML content. Be careful not to parse the missing elements. Remember the previous extracted information."},
                {"role": "user",
                "content": f"Previous extracted information:\n{prev_msg}\nHTML content is:\n{chunk_msg}"}
            ]
        return _messages
    
    def chunknize_html(
        self, 
        html: str, 
        mode: Literal["text", "dom"] = "text",
        chunk_size: int = 8000,
        overlap_size: int = 2000,
    ) -> List[str]:
        chunks = []
        # split html text to chunks by string length
        if mode == "text":
            start = 0
            while start < len(html):
                end = min(start + chunk_size, len(html))
                chunks.append(html[start:end])
                start += (chunk_size - overlap_size)
        # split html text to chunks by html dom tree
        elif mode == "dom":
            chunks = get_html_chunks(
                html,
                max_tokens=chunk_size,
                is_clean_html=True, 
                attr_cutoff_len=25 # TODO: what is this?
            )
        return chunks
    
    def count_tokens(self, text: str):
        return len(self.token_counter.encode(text))
    
    def parse_(
        self,
        html_chunk: str,
        previous_message: Optional[str] = None
    ) -> str:
        _messages = self.get_message(html_chunk, previous_message)
        ans = self.agent.chat.completions.create(
            model=self.model,
            messages=_messages,
            functions=[
                {
                    "name": "parse_fill_elements",
                    "description": "Parse all elements in HTML and extract filling details.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "data": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "Tag": {"type": "string",
                                                "description": "The tag of the element (Only contain input, select, textarea and datalist)."},
                                        "Type": {"type": "string",
                                                "description": "The type attribute of the tag if applicable."},
                                        "Name": {"type": "string",
                                                "description": "The name attribute of the tag."},
                                        "Id": {"type": "string",
                                            "description": "The id attribute of the tag."},
                                        "Label": {"type": "string",
                                                "description": "English only. The label and information which can associate with the fill element. If the element is a checkbox or radio button, the 'Label' attribute will include the premise information and its text. If the element is a select element, the 'Label' attribute will include the brief summary of the premise information and its options. Don't worry about the premise information getting too long, just summarize it briefly (don't make it too long) and put it in front of the first answer (not for Children). Be sure to remove newline characters and redundant spaces."},
                                        'Children': {"type": "array",
                                                    "description": "A list of child elements which has the same structure and properties as items. If an element has logic that affects other elements, such as checkboxes enabling or showing other input fields, the affected elements will be listed here. Don't put option tags in here.",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "Tag": {"type": "string"},
                                                            "Type": {"type": "string"},
                                                            "Name": {"type": "string"},
                                                            "Id": {"type": "string"},
                                                            "Label": {"type": "string"},
                                                            "Children": {
                                                                "type": "array",
                                                                "items": {}
                                                            }
                                                        },
                                                        "required": ["Tag", "Id", "Label", "Children"]
                                                    }
                                                    },
                                    },
                                    "required": ["Tag", "Id", "Label", "Children"]
                                }
                            }
                        },
                        "required": ["data"]
                    }
                }
            ],
            function_call={
                "name": "parse_fill_elements"
            },
            # stream=True
        )
        result = ans.choices[0].message.function_call.arguments
        return str(result)
    
    def parse_html(
        self, 
        html: str,
        chunk_mode: Literal["text", "dom"] = "text",
        chunk_size: int = 8000,
        chunk_overlap: int = 2000,
    ):
        html_chunks = self.chunknize_html(
            html,
            mode=chunk_mode,
            chunk_size=chunk_size,
            overlap_size=chunk_overlap,
        )
        
        prev_msg = None
        parse_results = []
        
        for html_chunk in html_chunks:
            res = self.parse_(
                html_chunk,
                prev_msg
            )
            # parse result to list of dict
            res = json.loads(res)
            if "data" in res:
                assert isinstance(res["data"], list)
                parse_results += res["data"]
                if len(parse_results) > 0:
                    prev_msg = parse_results[-1]
            
        return parse_results
            
        
    
    

    
    
    