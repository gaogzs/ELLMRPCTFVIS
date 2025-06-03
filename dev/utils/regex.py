import re

def divide_response_parts(response_txt: str) -> list:
    sections = re.split(r"-- \*\*.+\n", response_txt)
    # print([section.strip() for section in sections if section.strip()])
    return [section.strip() for section in sections if section.strip()]

def get_relation_params(relation_str: str) -> list:
    match = re.search(r'\(([^()]*)\)', relation_str)
    if match:
        matched_text = match.group(1)
        params = matched_text.split(",")
        params = [param.strip() for param in params]
        return params
    else:
        return []