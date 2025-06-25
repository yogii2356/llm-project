from utils.preprocessor import extract_text_from_folder
import gradio as gr
# from utils.preprocessor import preprocess_image, convert_pdf_to_image
from utils.ocr_engine import extract_text_from_image
# from utils.extractor import extract_invoice_fields
import google.generativeai as genai
import json
import os
import time
import re

json_responce = ""
def save_output(llm_response, output_file='output/invoice_data.json'):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Extract the JSON content between triple backticks
    match = re.search(r"```(?:json)?\s*(\[\s*\{.*?\}\s*\])\s*```", llm_response, re.DOTALL)


    if not match:
        print("No valid JSON block found in LLM response.")
        return
    
    try:
        cleaned_json_str = match.group(1)
        parsed_data = json.loads(cleaned_json_str)

        # Save to file
        with open(output_file, 'a', encoding='utf-8') as f:
            json.dump(parsed_data, f, indent=4)
        print(f"✅ JSON saved to {output_file}")

    except json.JSONDecodeError as e:
        print("❌ JSON decoding error:", e)


def ask_llm_about_invoice( model, text):
    
    # prompt = f"""
    #         You are a finance domain assistant specialized in reading and interpreting structured invoice data.

    #         Below is the extracted JSON data parsed from a scanned or uploaded invoice:

    #         {json.dumps(data, indent=4)}

    #         Your tasks:

    #         1. Convert this JSON into a clean and readable summary, formatted like a structured invoice.
    #         2. Extract and clearly highlight the following key details:
    #         - Invoice Number
    #         - Invoice Date
    #         - Total Invoice Amount
    #         - Buyer and Seller/Party Names and Addresses
    #         - GSTIN Numbers (if available)
    #         - Item Descriptions and Quantities
            
    #          {json.dumps(data, indent=4)}

    #         3. provide number of items and their prices along with cgst, sgst and total ammount
    #         4. Explain each field briefly in layman's terms.
    #         5. Point out any missing, incomplete, or ambiguous fields in the data.
    #         6. Highlight if any tax values seem incorrect or inconsistent based on the total.

    #         Be precise and concise in your response. Use bullet points or sections to improve readability. This output will help finance teams verify invoice integrity.
# """
    # prompt = f"""
    # You are a financial document assistant.

    # Below is the raw invoice text:
    
    # {text}
    
    # Your job is to:
    #     1. Return a corrected JSON version  fields below mentioned filled accurately.
    # #         2. Extract and clearly highlight the following key details:
    # #         - Invoice Number
    # #         - Invoice Date
    # #         - Total Invoice Amount
    # #         - Buyer and Seller/Party Names and Addresses
    # #         - GSTIN Numbers (if available)
    # #         - Item Descriptions and Quantities
    #     """


#     prompt = f"""
#             You are a finance domain assistant specialized in reading and interpreting structured invoice data.

#             Below is the extracted JSON data parsed from a scanned or uploaded invoice:

#             {json.dumps(data, indent=4)}

#             provide number of items and their prices along with cgst, sgst and total ammount
        

#             Be precise and concise in your response. Use bullet points or sections to improve readability. This output will help finance teams verify invoice integrity.
# """
    
    prompt = f"""

You are a financial document assistant.
Below is the raw  multiple invoices text:

{text}
Your job is to:
1. Extract and return ONLY the following fields in clean JSON format for all invoices:
   - invoice_number
   - company_name (Seller)
   - seller_address
   - seller_gstin
   - buyer_name
   - buyer_address
   - buyer_gstin
   - items (a list with item S.N., descriptions of Goods,HSN/SAC code, quantity, unit, list price, Discount, price and amount)
   - subtotal_before_gst
   - cgst
   - sgst
   - total_gst (sum of cgst and sgst or igst)
   - total_amount_after_gst
   - bank_details

Ensure the response is strictly a valid JSON object without any explanation or markdown formatting. Example format:

{{
    "invoice_number": "...",
    "company_name": "...",
    "seller_address": "...",
    "seller_gstin": "...",
    "buyer_name": "...",
    "buyer_address": "...",
    "buyer_gstin": "...",
    "items": [
        {{
            "S.N.": ...,
            "description of goods": "...",
            "HSN/SAG code": ...,
            "quantity": ...,
            "unit": "..."
            "list price": ...,
            "Discount": ...,
            "price": ...,
            "amount": ...,
        }}
    ],
    "subtotal_before_gst": ...,
    "cgst": ...,
    "sgst": ...,
    "total_gst": ...,
    "total_amount_after_gst": ...,
    "bank_details": ...
}}
"""

    
    
    for attempt in range(2):  # Retry up to 3 times
        try:
            response = model.generate_content(prompt)
            print(f"followimg is the responce of llm :\n{response.text}")
            global json_responce
            json_responce = response.text
            return response.text
        except Exception as e:
            print(f"LLM error: {e}")
            print("Rate limit hit or other error. Waiting 60 seconds...")
            time.sleep(60)
    return "LLM response could not be retrieved after multiple attempts."


def chat_with_invoice(message,history=None):
        system = f"""you are a expert charted account. You will receive bill invoices from different firms/companies/organizations. We will provide a json data to you now you have to take a look into that data and answer me correctly as per indian tax law.
        """
        prompt=f"""{system} \n
        your are provided with a json responce from a llm which is delimited by triple backtics.
        llm responce = ``` {json_responce}```
        your task is to answer users quesitons according to the llm and json responce provided to you. The user question is delimited by double backtics .
        user Question = ``{message}``
        your answer should be in a readble string not in json format."""
        genai.configure(api_key=Gemini_api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        gemini_responce = model.generate_content(prompt)
        # print(f"promt for gemini : {prompt}")
        return gemini_responce.text
    

def main(folder_path, Gemini_api_key):
    print("=== MAIN STARTED ===")

    # Step 1: Convert PDF to image if needed
    # if file_path.endswith('.pdf'):
    #     images = extract_text_from_pdf(file_path)
    #     image_path = 'temp_invoice.png'
    #     images[0].save(image_path)
    # else:
    #     image_path = file_path

    # Step 2: Preprocess image and extract text
    # text = extract_text_from_pdf(file_path)
    text = extract_text_from_folder(folder_path)
    print("Extracted Text:\n", text)
    
# Save the text to a file
    os.makedirs('output', exist_ok=True)
    with open('output/parsed_invoice_text.txt', 'a', encoding='utf-8') as f:
        f.write("Extracted Text:\n")
        f.write(text)


    # Step 3: Extract structured data from text
    # parsed_data = extract_invoice_fields(text)
    # print("Extracted Data:\n", parsed_data)
    # with open('output/parsed_invoice_data.txt', 'w') as f:
    #     f.write("Extracted Data:\n")
    #     f.write(json.dumps(parsed_data, indent=4))
    # 

    
    # Step 5: Configure Gemini and query LLM
    genai.configure(api_key=Gemini_api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    llm_response = ask_llm_about_invoice(model, text)
    save_output(llm_response)
    with open("data.json", "w", encoding="utf-8") as f:
     json.dump(llm_response, f, indent=4)

    # Step 6: Show LLM's formatted/explained output
    
    gr.ChatInterface(
    fn=chat_with_invoice,
    type="messages",
    title="Invoice Q&A Bot",
    examples=["What's the total amount?", "List item details", "Who is the buyer?"]
).launch()
    

if __name__ == '__main__':
    folder_path = 'data/'  # Change this path as needed
    Gemini_api_key = 'AIzaSyB4UR9kwtUtEm3Uv4WHHji0R_y6blnI2Fc'  # Replace with your actual Gemini API key
    main(folder_path, Gemini_api_key)
   
    
