import os
from dotenv import load_dotenv
import boto3

load_dotenv()  # loads .env into environment variables

s3 = boto3.client("s3")
bucket = os.getenv("S3_BUCKET")

print(s3.list_objects_v2(Bucket=bucket, MaxKeys=5))
