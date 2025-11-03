from pydantic import BaseModel, Field
from typing import List, Optional

# --- NEW: Multilingual String Model ---
class LangString(BaseModel):
    """
    Represents a string value that may exist in multiple languages.
    At least one language field should be populated.
    """
    en: Optional[str] = Field(None, description="The extracted text in English.")
    ar: Optional[str] = Field(None, description="The extracted text in Arabic.")


class Nutrient(BaseModel):
    """Represents a single nutrient row from the nutrition facts table."""
    name: LangString = Field(..., description="Extract the name of the nutrient (e.g., 'Total Fat', 'Sodium', 'Sugars') in English and Arabic.")
    quantity: Optional[float] = Field(None, description="Extract only the numerical value of the nutrient's quantity (e.g., for '10g', extract 10).")
    unit: Optional[LangString] = Field(None, description="Extract the unit of measurement for the nutrient (e.g., 'g', 'mg', 'kcal') in English and Arabic.")
    daily_value_percent: Optional[float] = Field(None, description="Extract only the numerical percentage for the Daily Value (%DV), if available (e.g., for '15%', extract 15).")

class Ingredient(BaseModel):
    """Represents an individual ingredient from the ingredients list."""
    name: LangString = Field(..., description="Extract the name of a single ingredient (e.g., 'Enriched Flour', 'Palm Oil') in English and Arabic.")
    quantity: Optional[LangString] = Field(None, description="If a quantity or percentage is listed next to an ingredient, extract it as a string (e.g., '5%') in English and Arabic.")
    is_allergen: bool = Field(False, description="Set to true if this ingredient is highlighted, in bold, or explicitly listed in an allergen warning.")

class Dimensions(BaseModel):
    """Represents the physical dimensions of the product packaging, if mentioned."""
    length: Optional[float] = Field(None, description="Extract the numerical value for the package's length, if specified.")
    width: Optional[float] = Field(None, description="Extract the numerical value for the package's width, if specified.")
    height: Optional[float] = Field(None, description="Extract the numerical value for the package's height, if specified.")
    unit: Optional[LangString] = Field("cm", description="Extract the unit of measurement for the dimensions (e.g., 'cm', 'in', 'mm') in English and Arabic.")

class ProductContent(BaseModel):
    """Represents the net weight or volume of the product."""
    value: float = Field(..., description="Extract the numerical value of the product's net weight or volume (e.g., from 'NET WT 500 g', extract 500).")
    unit: LangString = Field(..., description="Extract the unit of the product's net weight or volume (e.g., 'g', 'kg', 'ml', 'L', 'oz') in English and Arabic.")

class BasicAnnotationSchema(BaseModel):
    """Represents a bounding box for a detected text or object."""
    x: int = Field(..., description="The x-coordinate of the top-left corner of the bounding box.")
    y: int = Field(..., description="The y-coordinate of the top-left corner of the bounding box.")
    width: int = Field(..., description="The width of the bounding box in pixels.")
    height: int = Field(..., description="The height of the bounding box in pixels.")
    label: str = Field(..., description="The specific label or class name of the detected object (e.g., 'product_name', 'brand').")


class ProductInfo(BaseModel):
    """Structured representation of all extracted product data from an image."""
    product_name: LangString = Field(..., description="Extract the most prominent, primary name of the product in English and Arabic.")
    brand: Optional[LangString] = Field(None, description="Identify and extract the brand name in English and Arabic.")
    flavor: Optional[LangString] = Field(None, description="Extract the specific flavor of the product if it is mentioned (e.g., 'Chocolate Chip', 'Lemon Lime') in English and Arabic.")
    product_description: Optional[LangString] = Field(None, description="Extract any general descriptive marketing text or slogan in English and Arabic.")
    
    price: Optional[str] = Field(None, description="Extract the price of the item as a text string, including the currency symbol, if visible (e.g., '$4.99', '₹120').")
    is_promotional: bool = Field(False, description="Set to true if words indicating a promotion like 'Special Offer', 'Sale', '2 for 1', or 'New' are clearly visible on the packaging.")
    
    net_content: Optional[ProductContent] = Field(None, description="Extract the net weight or volume information (e.g., 'Net Wt 500g', 'Volume 1L').")
    item_count: Optional[int] = Field(None, description="If the package contains multiple individual items, extract the count (e.g., for '6 Pack Cans', extract 6).")
    dimensions: Optional[Dimensions] = Field(None, description="Extract the physical package dimensions if they are listed (e.g., '10cm x 5cm x 2cm').")
    
    barcode: Optional[str] = Field(None, description="Extract the sequence of numerical digits from the product's barcode (UPC or EAN), if visible.")
    
    serving_size: Optional[LangString] = Field(None, description="From the nutrition facts panel, extract the serving size text (e.g., '1 cup (228g)') in English and Arabic.")
    servings_per_container: Optional[LangString] = Field(None, description="From the nutrition facts panel, extract the number of servings per container (e.g., 'about 2.5', '8') in English and Arabic.")

    ingredients: Optional[List[Ingredient]] = Field(None, description="Parse and extract each item from the complete ingredients list.")
    nutrition_facts: Optional[List[Nutrient]] = Field(None, description="Extract all available nutrient rows from the nutrition facts table.")
    
    allergens: Optional[List[LangString]] = Field(None, description="Extract the text from any dedicated allergen statement (e.g., 'Contains Wheat, Milk, and Soy.') in English and Arabic.")
    claims: Optional[List[LangString]] = Field(None, description="Extract any marketing or health claims (e.g., 'High in Fiber', 'No Added Sugar', 'Gluten Free') in English and Arabic.")
    certifications: Optional[List[LangString]] = Field(None, description="Extract the names of any official certifications (e.g., 'USDA Organic', 'Halal', 'Non-GMO Project Verified') in English and Arabic.")
    
    manufacturer: Optional[LangString] = Field(None, description="Extract the company name listed after a phrase like 'Manufactured by:' in English and Arabic.")
    distributor: Optional[LangString] = Field(None, description="Extract the company name listed after a phrase like 'Distributed by:' in English and Arabic.")
    country_of_origin: Optional[LangString] = Field(None, description="Extract the country name from phrases like 'Made in', 'Product of' in English and Arabic.")
    
    storage_instructions: Optional[LangString] = Field(None, description="Extract any instructions for storing the product (e.g., 'Refrigerate after opening') in English and Arabic.")
    expiration_date: Optional[str] = Field(None, description="Find and extract the expiration date, which may be labeled as 'Best By', 'Use By', or 'EXP'.")
    batch_number: Optional[str] = Field(None, description="Find and extract the production lot or batch number, often labeled 'Lot No.' or 'Batch'.")


class FullAnnotationSchema(BaseModel):
    """The complete schema for an annotated image, containing image metadata and extracted product details."""
    image_id: str = Field(..., description="A unique identifier for the image file.")
    product_details: ProductInfo = Field(..., description="A nested object containing all extracted product details.")


# --- Compatibility Aliases ---
basic_annotation_schema = BasicAnnotationSchema
full_annotation_schema = FullAnnotationSchema