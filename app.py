import streamlit as st
import base64
from mistralai import Mistral
from mistralai.extra import response_format_from_pydantic_model
from scheamas.v2.schemas import ProductInfo, basic_annotation_schema, full_annotation_schema

st.set_page_config(layout="wide")
st.title("🛍️ Product OCR & Annotation Visualizer")
st.markdown("Upload one or more product images. The app extracts structured details and annotations using Mistral OCR.")

# --- Helper functions ---
def encode_file(file_bytes):
    """Encode bytes into base64 for OCR API."""
    return base64.b64encode(file_bytes).decode("utf-8")

def analyze_image(api_key, image_data, mime_type):
    """Call Mistral OCR for a single image."""
    try:
        client = Mistral(api_key=api_key)
        payload = {
            "type": "image_url",
            "image_url": f"data:{mime_type};base64,{image_data}"
        }
        response = client.ocr.process(
            model="mistral-ocr-latest",
            document=payload,
            document_annotation_format=response_format_from_pydantic_model(full_annotation_schema)
        )
        return response.document_annotation
    except Exception as e:
        st.error(f"Error processing image: {e}")
        return None

def display_results(annotation_json, filename):
    """Pretty-print the structured OCR data."""
    st.success(f"✅ Processed: {filename}")
    try:
        result = full_annotation_schema.model_validate_json(annotation_json)
        st.subheader(f"📦 Product: {result.product_details.product_name}")
        st.write(f"**Brand:** {result.product_details.brand or 'N/A'}")
        st.write(f"**Price:** {result.product_details.price or 'N/A'}")


        with st.expander("Show Raw JSON"):
            st.json(annotation_json)
    except Exception as e:
        st.error(f"Parsing error: {e}")
        st.text_area("Raw response", annotation_json)

# --- UI Section ---
api_key = st.text_input("Enter your Mistral API Key:", type="password")
uploaded_files = st.file_uploader("Upload product images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files and st.button("Start Analysis"):
    if not api_key:
        st.warning("Please enter your Mistral API key first.")
    else:
        for uploaded_file in uploaded_files:
            with st.spinner(f"Analyzing {uploaded_file.name}..."):
                encoded = encode_file(uploaded_file.getvalue())
                result_str = analyze_image(api_key, encoded, uploaded_file.type)
                if result_str:
                    display_results(result_str, uploaded_file.name)
