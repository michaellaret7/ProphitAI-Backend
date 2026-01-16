import os
from dotenv import load_dotenv
import boto3

load_dotenv()  # loads .env into environment variables

s3 = boto3.client("s3")
bucket = os.getenv("S3_BUCKET")


