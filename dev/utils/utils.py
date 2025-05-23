def dict_pretty_str(data: dict) -> str:
        out_str = ""
        for key, value in data.items():
            out_str += f"{key}: {value}\n"
        return out_str