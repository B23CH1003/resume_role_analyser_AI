from pdf_reader import extract_text

text = extract_text("resume_exp.pdf")

print(text[:1000])