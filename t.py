from app.core.foundry.ingestion.modal_ops import ModalPDFClient                                                                                                                                                                               

client = ModalPDFClient()
results = client.extract_batch_from_s3([
    "s3://prophitai-s3-bucket/pdfs/equity_research/1Q26 EPS_ Trimming Estimates and Price Target on the 2Q26 Gu DHI.pdf",
    "s3://prophitai-s3-bucket/pdfs/equity_research/Q4 Sales Miss, ABT.pdf",
    "s3://prophitai-s3-bucket/pdfs/equity_research/With CoreWeave Stock Surging, SuRo's NAV Math Has Gotten Eve.pdf",
    "s3://prophitai-s3-bucket/pdfs/equity_research/Turning to Unit Growth Story w_ Global Spheres + Multiyear P SPHR.pdf"
])

for r in results:
    print(f"{r['s3_uri']}: {r['char_count']} chars")