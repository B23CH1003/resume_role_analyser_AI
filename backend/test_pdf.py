from pdf_reader import extract_text

text = extract_text("resume.pdf")

print(text[:1000])