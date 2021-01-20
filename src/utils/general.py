import emoji

def split_list(arr, size):
     arrs = []
     while len(arr) > size:
         pice = arr[:size]
         arrs.append(pice)
         arr   = arr[size:]
     arrs.append(arr)
     return arrs

def text_to_emojis(text):
    text = str(text)
    emojis = []

    for char in text:
        if char.isdigit():
            emoji_format = ":keycap_{char}:"
        elif char == "-":
            emoji_format = ":heavy_minus_sign:"
        elif char == ".":
            emoji_format = ":black_small_square:"
        else:
            emoji_format = ":regional_indicator_symbol_letter_{char}:"

        emojis.append(emoji.emojize(emoji_format.format(char = char), use_aliases=True))

    return emojis

def html_to_discord(text):
    tags = {
        "i"      : "*",
        "strong" : "**",
        "em"     : "",
        "sub"    : "",
        "xref"   : "",
    }

    for tag, replacement in tags.items():
        text = text.replace(f"<{tag}>", replacement)
        text = text.replace(f"</{tag}>", replacement)

    return text.strip()


