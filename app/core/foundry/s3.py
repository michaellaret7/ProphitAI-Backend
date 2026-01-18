import requests
import boto3
from dotenv import load_dotenv

load_dotenv()

# ————— Configure —————
url = "https://www.kerrisdalecap.com/wp-content/uploads/2025/09/Kerrisdale-CoreWeave.pdf"
bucket = "prophitai-s3-bucket"
key = "pdfs/Kerrisdale-CoreWeave-09-2025.pdf"

s3 = boto3.client("s3")

# ————— Stream from URL and upload —————
# stream=True keeps the connection open
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
with requests.get(url, headers=headers, stream=True) as response:
    response.raise_for_status()
    
    # Ensure we get the actual decoded content (e.g. if gzipped)
    response.raw.decode_content = True
    
    # Upload with metadata so browsers handle it correctly
    s3.upload_fileobj(
        response.raw, 
        bucket, 
        key,
        ExtraArgs={'ContentType': response.headers.get('Content-Type', 'application/pdf')}
    )

print(f"Uploaded to s3://{bucket}/{key}")
