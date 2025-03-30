import fitz
import openai
from tqdm import tqdm

openai_key = "INPUT YOUR KEY HERE"

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text("text") for page in doc)
    return text

def chunk_text(text, chunk_size= 8000):
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    return chunks

def summarize_text(text,openai_key):
    chunks = chunk_text(text)   # split the text into manageable chunks (roadmap: to fix this to handle long pdfs better)
    summary = ""

    for chunk in tqdm(chunks, desc="Summarizing", unit="chunk"):
        client = openai.OpenAI(api_key=openai_key)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[ 
                {"role": "system", "content": "Summarize the following case law, highlighting key legal issues, judgments, and precedent."},
                {"role": "user", "content": chunk}
            ],
            max_tokens= 4000
        )
        summary += response.choices[0].message.content + "\n"
    
    return summary

def main():
    pdf_path = input("Enter the path to the case law PDF: ")
    text = extract_text_from_pdf(pdf_path)
    summary = summarize_text(text,openai_key)
    print("\nSummary of Case Law:\n")
    print(summary)

if __name__ == "__main__":
    main()
