from app.core.foundry.ingestion import Ingestor

ingestor = Ingestor(use_modal_gpu=True)
doc = ingestor.process("s3://prophitai-s3-bucket/pdfs/equity_research/1Q26 EPS_ Trimming Estimates and Price Target on the 2Q26 Gu DHI.pdf")
print(doc.content[:500])