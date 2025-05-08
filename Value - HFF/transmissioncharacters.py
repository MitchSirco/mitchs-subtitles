from tkinter import Tk
def format_text_char(input_text, line_length=16, corner="\u200b"):
    # Calculate available space for text (accounting for corners and spaces)
    corner_len = len(corner)
    text_width = line_length - 2 * (corner_len + 1)  # 55 - 2*(3+1) = 47
    print(input_text)
    print(len(input_text))
    # Preprocess <br> tags to 10 spaces
    processed_text = input_text.replace("<br>", "          ")
    
    buffer = []
    lines = []
    
    for char in processed_text:
        buffer.append(char)
        
        # Trim buffer to maximum allowed length
        if len(buffer) > text_width:
            buffer = buffer[-text_width:]
        
        # Create text line with padding
        current_line = ''.join(buffer).rjust(text_width)
        
        # Build final formatted line
        formatted = f"{corner}{current_line}{corner}"
        lines.append(formatted)
    
    return lines

# Example usage
input_text = "Ohhhhhhhhhhhhhhhhhhh Oh Ohhhhhh        \u200b"
#input_text = "Ooooooooooohh         \u200b"
#input_text = "Ohh Ooohhhhhhhhhhhh"
#input_text = "CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAaaaaaaaaaaaaᵃᵃᵃᵃᵃᵃⁿⁿⁿⁿⁿⁿⁿ"
#input_text = "Ohhhhh-Ohhhhhhh-Oh-Oh-Ohhhhhhhhhhhhhhh" 
#input_text = "HAAAAAAAAAAAaaaaaaaannnndddsssss"
#input_text = "jgkrdlögjdrgklödfgjfkgöldfjgkdflögjfdgklfö"
#input_text = "HAAAAAAAAAaaaaaaaaaaaaaaaaaaaaaaaaaaaaandds      \u200b"
#input_text = "oooooooooooooooOOOOOOOOOOOOOOOOOOoooooooooooooooooooooh    \u200b"
#input_text = "aaaaaaaaaaaaaaaaaaaaaaaaaaaAAAAAaaaaaaaaaaaaaaaaaaaaall   \u200b"
#ᵒʷⁿ
result = format_text_char(input_text)


actualresult = ""

for line in result:  # Print first 10 lines as example
    actualresult += line + "\n"
    print(line)
    
    

actualresult = actualresult.rstrip(actualresult[-1])
r = Tk()
r.withdraw()
r.clipboard_clear()
r.clipboard_append(actualresult)
r.update() # now it stays on the clipboard after the window is closed
r.destroy()