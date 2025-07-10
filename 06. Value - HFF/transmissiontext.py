def format_text(input_text, line_length=55, corner="l\u200bl"):
    corner_length = len(corner)
    middle_length = line_length - 2 * corner_length
    available_text_length = middle_length  # Account for surrounding spaces
    print(corner_length)
    print(middle_length)
    print(available_text_length)
    words = input_text.split()
    current_text = ""
    lines = []
    
    for word in words:
        if word == "<br>":
            # Add 10 spaces to the left
            current_text =  current_text + "          "
        else:
            # Add normal word with space separator
            current_text = f"{current_text} {word}".strip() if current_text else word
        
        # Truncate from left if needed
        if len(current_text) > available_text_length:
            current_text = current_text[-available_text_length:]
        
        # Pad with spaces on left if needed
        current_text = current_text.rjust(available_text_length)
        
        # Create the line with spaces and corners
        formatted_line = f"{corner} {current_text} {corner}"
        lines.append(formatted_line)
    
    return lines

# Example usage
input_text = "The Incident is reported last night, after multiple people were found dead inside a conference room of the Hirobusha corp complex in hamburg. <br> <br> <br> They appear to all show signs of rampant mutation and bitemarks. <br> <br> <br> Officials deny any connection to Hirobusha corp: Their brand new neural implants, <br> which are currently under investigation for posing risk to public health after showing many defects. <br> <br> The victims seem to have lost their minds after their devices malfunctioned and sent them into frenzy. <br> <br> <br> <br> It also destabilized their genetic code promoting rapid cell growth all throughout their bodies. <br> <br> <br> How this device ever got approved by the FDA is still a mystery as this is a very dangerous combination. <br> <br> <br> <br> "

#input_text = "OOOOhhhhhh Ohhhhhh"
result = format_text(input_text)

for line in result:
    print(line)
