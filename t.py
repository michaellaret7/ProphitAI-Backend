#!/usr/bin/env python3
"""
Quant Trading Strategy Papers -> S3 Uploader
=============================================
Downloads quantitative and algorithmic trading strategy papers from
arXiv, SSRN, and other open-access sources, then uploads them to S3.

Usage:
    pip install boto3 requests
    python upload_trading_papers_to_s3.py

Configure your AWS credentials below or via environment variables.
"""

import os
import sys
import time
import hashlib
import requests
import boto3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── CONFIG ───────────────────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "AKIAZ5TC5H7Y4JDYQMUG")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "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")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
S3_BUCKET = "prophitai-s3-bucket"
S3_PREFIX = "pdfs/trading_strategies/not_embedded/"
DOWNLOAD_DIR = Path("./trading_papers_download")
MAX_WORKERS = 5  # parallel downloads
# ──────────────────────────────────────────────────────────────────────────────

# All papers to download — (filename, url) tuples
# ArXiv papers use the /pdf/ endpoint which returns PDF directly.
# SSRN papers use their Delivery.cfm PDF links.

PAPERS = [
    # ═══════════════════════════════════════════════════════════════════════════
    # DEEP REINFORCEMENT LEARNING FOR TRADING
    # ═══════════════════════════════════════════════════════════════════════════
    ("arxiv_2312.15730_Deep_RL_for_Quantitative_Trading.pdf",
     "https://arxiv.org/pdf/2312.15730"),

    ("arxiv_2106.00123_Deep_RL_in_Quant_Algorithmic_Trading_Review.pdf",
     "https://arxiv.org/pdf/2106.00123"),

    ("arxiv_2411.07585_RL_Framework_for_Quantitative_Trading.pdf",
     "https://arxiv.org/pdf/2411.07585"),

    ("arxiv_2310.05551_Logic_Q_DRL_Quantitative_Trading.pdf",
     "https://arxiv.org/pdf/2310.05551"),

    ("arxiv_2111.09395_FinRL_Deep_RL_Automate_Trading.pdf",
     "https://arxiv.org/pdf/2111.09395"),

    ("arxiv_2304.06037_Quantitative_Trading_Deep_Q_Learning.pdf",
     "https://arxiv.org/pdf/2304.06037"),

    ("arxiv_2004.06627_Deep_RL_Applied_to_Algorithmic_Trading.pdf",
     "https://arxiv.org/pdf/2004.06627"),

    ("arxiv_2509.09176_Quantum_Enhanced_RL_Algorithmic_Trading.pdf",
     "https://arxiv.org/pdf/2509.09176"),

    ("arxiv_2510.10526_LLM_RL_Sentiment_Driven_Quant_Trading.pdf",
     "https://arxiv.org/pdf/2510.10526"),

    # ═══════════════════════════════════════════════════════════════════════════
    # TRANSFORMER / ATTENTION-BASED TRADING
    # ═══════════════════════════════════════════════════════════════════════════
    ("arxiv_2404.00424_Quantformer_Transformer_Trading_Strategy.pdf",
     "https://arxiv.org/pdf/2404.00424"),

    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICAL ARBITRAGE / PAIRS TRADING / MEAN REVERSION
    # ═══════════════════════════════════════════════════════════════════════════
    ("arxiv_1803.02974_Optimal_Portfolio_Statistical_Arbitrage.pdf",
     "https://arxiv.org/pdf/1803.02974"),

    ("arxiv_2105.13727_Slow_Momentum_Fast_Reversion_DL_Trading.pdf",
     "https://arxiv.org/pdf/2105.13727"),

    ("arxiv_0808.1710_Dynamic_Mean_Reverting_Spreads_StatArb.pdf",
     "https://arxiv.org/pdf/0808.1710"),

    ("arxiv_2403.12180_Advanced_StatArb_with_RL.pdf",
     "https://arxiv.org/pdf/2403.12180"),

    ("arxiv_2402.08233_End_to_End_StatArb_Autoencoder.pdf",
     "https://arxiv.org/pdf/2402.08233"),

    ("arxiv_2406.10695_StatArb_Multi_Pair_Graph_Clustering.pdf",
     "https://arxiv.org/pdf/2406.10695"),

    ("arxiv_1811.00200_Online_Learning_Statistical_Arbitrage.pdf",
     "https://arxiv.org/pdf/1811.00200"),

    ("arxiv_1608.03636_General_Framework_Pairs_Trading.pdf",
     "https://arxiv.org/pdf/1608.03636"),

    ("arxiv_2512.02037_StatArb_Polish_Equities_Deep_Learning.pdf",
     "https://arxiv.org/pdf/2512.02037"),

    # ═══════════════════════════════════════════════════════════════════════════
    # OPTIONS PRICING, HEDGING & DERIVATIVES STRATEGIES
    # ═══════════════════════════════════════════════════════════════════════════
    ("arxiv_2511.20837_Deep_Learning_Pricing_Hedging_European_Options.pdf",
     "https://arxiv.org/pdf/2511.20837"),

    ("arxiv_1912.11060_Pricing_Hedging_American_Options_DL.pdf",
     "https://arxiv.org/pdf/1912.11060"),

    ("arxiv_2509.12753_DeltaHedge_Multi_Agent_Portfolio_Options.pdf",
     "https://arxiv.org/pdf/2509.12753"),

    ("arxiv_2211.15912_Optimizing_Stock_Option_Forecasting_ML.pdf",
     "https://arxiv.org/pdf/2211.15912"),

    ("arxiv_2512.12420_Deep_Hedging_RL_Option_Risk_Management.pdf",
     "https://arxiv.org/pdf/2512.12420"),

    ("arxiv_2010.12245_Option_Hedging_Risk_Averse_RL.pdf",
     "https://arxiv.org/pdf/2010.12245"),

    ("arxiv_2111.03477_Data_Driven_Hedging_Stock_Index_Options.pdf",
     "https://arxiv.org/pdf/2111.03477"),

    ("arxiv_2405.08602_Deep_RL_American_Put_Option_Hedging.pdf",
     "https://arxiv.org/pdf/2405.08602"),

    ("arxiv_2405.06774_Hedging_American_Put_Options_Deep_RL.pdf",
     "https://arxiv.org/pdf/2405.06774"),

    ("arxiv_2507.01972_Accelerated_Portfolio_Optimization_Option_Pricing_RL.pdf",
     "https://arxiv.org/pdf/2507.01972"),

    # ═══════════════════════════════════════════════════════════════════════════
    # MARKET MAKING & HIGH FREQUENCY TRADING
    # ═══════════════════════════════════════════════════════════════════════════
    ("arxiv_1106.5040_Optimal_HFT_Limit_Market_Orders.pdf",
     "https://arxiv.org/pdf/1106.5040"),

    ("arxiv_1903.07222_Market_Making_Limit_Order_Book.pdf",
     "https://arxiv.org/pdf/1903.07222"),

    ("arxiv_2109.15110_Deep_Hawkes_HF_Market_Making.pdf",
     "https://arxiv.org/pdf/2109.15110"),

    ("arxiv_1806.05101_Order_Book_Modelling_Market_Making.pdf",
     "https://arxiv.org/pdf/1806.05101"),

    ("arxiv_2412.16850_Limit_Order_Book_HFT_Rough_Volatility.pdf",
     "https://arxiv.org/pdf/2412.16850"),

    ("arxiv_2305.15821_Market_Making_Deep_RL_LOB.pdf",
     "https://arxiv.org/pdf/2305.15821"),

    ("arxiv_1605.01862_Optimal_Market_Making.pdf",
     "https://arxiv.org/pdf/1605.01862"),

    # ═══════════════════════════════════════════════════════════════════════════
    # SENTIMENT ANALYSIS & NLP FOR TRADING
    # ═══════════════════════════════════════════════════════════════════════════
    ("arxiv_2412.19245_Sentiment_Trading_with_LLMs.pdf",
     "https://arxiv.org/pdf/2412.19245"),

    ("arxiv_2403.12285_FinLlama_Sentiment_Algorithmic_Trading.pdf",
     "https://arxiv.org/pdf/2403.12285"),

    ("arxiv_2404.00012_Stress_Index_Strategy_News_Sentiment.pdf",
     "https://arxiv.org/pdf/2404.00012"),

    ("arxiv_2502.01574_End_to_End_LLM_Enhanced_Trading_System.pdf",
     "https://arxiv.org/pdf/2502.01574"),

    ("arxiv_2507.18417_FinDPO_Financial_Sentiment_Algo_Trading.pdf",
     "https://arxiv.org/pdf/2507.18417"),

    ("arxiv_2507.09739_Trading_Performance_Sentiment_LLMs_SP500.pdf",
     "https://arxiv.org/pdf/2507.09739"),

    # ═══════════════════════════════════════════════════════════════════════════
    # CRYPTOCURRENCY TRADING STRATEGIES
    # ═══════════════════════════════════════════════════════════════════════════
    ("arxiv_2506.11921_Dynamic_Grid_Trading_Strategy_Crypto.pdf",
     "https://arxiv.org/pdf/2506.11921"),

    ("arxiv_1911.11819_Crypto_Price_Prediction_SVM_Trading.pdf",
     "https://arxiv.org/pdf/1911.11819"),

    ("arxiv_2412.18202_Crypto_Trading_Autoencoder_CNN_GANs.pdf",
     "https://arxiv.org/pdf/2412.18202"),

    ("arxiv_2003.11352_Cryptocurrency_Trading_Comprehensive_Survey.pdf",
     "https://arxiv.org/pdf/2003.11352"),

    ("arxiv_2411.05829_RNN_Realtime_Crypto_Price_Trading.pdf",
     "https://arxiv.org/pdf/2411.05829"),

    ("arxiv_2109.14789_Bitcoin_Transaction_Strategy_Deep_RL.pdf",
     "https://arxiv.org/pdf/2109.14789"),

    ("arxiv_2105.06827_Profitable_Strategy_Crypto_ML.pdf",
     "https://arxiv.org/pdf/2105.06827"),

    ("arxiv_2510.07943_Agent_Based_Genetic_Algo_Crypto_Trading.pdf",
     "https://arxiv.org/pdf/2510.07943"),

    ("arxiv_2110.14936_Algorithmic_Trading_Strategies_Bitcoin.pdf",
     "https://arxiv.org/pdf/2110.14936"),

    ("arxiv_1612.01277_Crypto_Portfolio_Management_Deep_RL.pdf",
     "https://arxiv.org/pdf/1612.01277"),

    # ═══════════════════════════════════════════════════════════════════════════
    # KELLY CRITERION, RISK PARITY & POSITION SIZING
    # ═══════════════════════════════════════════════════════════════════════════
    ("arxiv_1710.00431_Kelly_Criterion_Portfolio_Optimization.pdf",
     "https://arxiv.org/pdf/1710.00431"),

    ("arxiv_1610.10029_Meta_CTA_Trading_Kelly_Criterion.pdf",
     "https://arxiv.org/pdf/1610.10029"),

    ("arxiv_2412.14144_Kelly_Criterion_Prediction_Markets.pdf",
     "https://arxiv.org/pdf/2412.14144"),

    ("arxiv_1806.05293_Kelly_Criterion_Stock_Markets_Framework.pdf",
     "https://arxiv.org/pdf/1806.05293"),

    ("arxiv_2402.15588_Sizing_Bets_Focused_Portfolio.pdf",
     "https://arxiv.org/pdf/2402.15588"),

    ("arxiv_2202.02728_Hierarchical_Risk_Parity_Min_Variance.pdf",
     "https://arxiv.org/pdf/2202.02728"),

    ("arxiv_2202.10721_Risk_Parity_Skewness_Factor_Investing.pdf",
     "https://arxiv.org/pdf/2202.10721"),

    # ═══════════════════════════════════════════════════════════════════════════
    # SSRN PAPERS - SYSTEMATIC & FACTOR TRADING
    # ═══════════════════════════════════════════════════════════════════════════
    ("ssrn_5278107_Course_Systematic_Trading_RMA.pdf",
     "https://papers.ssrn.com/sol3/Delivery.cfm/5278107.pdf?abstractid=5278107&mirid=1"),

    ("ssrn_5197573_Traditional_vs_Quant_Traders.pdf",
     "https://papers.ssrn.com/sol3/Delivery.cfm/5197573.pdf?abstractid=5197573&mirid=1"),

    ("ssrn_5225612_Quant_Alpha_Crypto_Factor_Models.pdf",
     "https://papers.ssrn.com/sol3/Delivery.cfm/5225612.pdf?abstractid=5225612&mirid=1"),

    ("ssrn_4647103_Futuretesting_Quantitative_Strategies.pdf",
     "https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID4728952_code802495.pdf?abstractid=4647103"),

    ("ssrn_5523259_Intro_Factor_Investing.pdf",
     "https://papers.ssrn.com/sol3/Delivery.cfm/5523259.pdf?abstractid=5523259&mirid=1"),

    ("ssrn_3904097_Algorithmic_Trading_Retail_Investors.pdf",
     "https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID3904097_code4795560.pdf?abstractid=3904097&mirid=1"),

    ("ssrn_3313364_Factor_Investing_Concept_to_Implementation.pdf",
     "https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID3467491_code2061164.pdf?abstractid=3313364&mirid=1"),

    ("ssrn_4315362_Data_to_Trade_ML_Quantitative_Trading.pdf",
     "https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID4315362_code3024096.pdf?abstractid=4315362&mirid=1"),

    # ═══════════════════════════════════════════════════════════════════════════
    # OTHER OPEN-ACCESS PAPERS
    # ═══════════════════════════════════════════════════════════════════════════
    ("wjaets_2024_Impact_Algorithmic_Trading_Stock_Market.pdf",
     "https://wjaets.com/sites/default/files/WJAETS-2024-0136.pdf"),

    # ═══════════════════════════════════════════════════════════════════════════
    # ADDITIONAL ARXIV — ML & DEEP LEARNING FOR TRADING
    # ═══════════════════════════════════════════════════════════════════════════
    ("arxiv_2502.07606_Algorithmic_Aspects_Strategic_Trading.pdf",
     "https://arxiv.org/pdf/2502.07606"),

    ("arxiv_2506.06356_Deep_Learning_Multi_Day_Turnover_Quant.pdf",
     "https://arxiv.org/pdf/2506.06356"),

    ("arxiv_2101.03086_Market_Making_Stochastic_Liquidity.pdf",
     "https://arxiv.org/pdf/2101.03086"),

    ("arxiv_2109.10814_Fractional_Growth_Portfolio_Investment.pdf",
     "https://arxiv.org/pdf/2109.10814"),

    ("arxiv_2507.05994_Beating_Best_Constant_Rebalancing_Kelly.pdf",
     "https://arxiv.org/pdf/2507.05994"),

    ("arxiv_2508.18868_Tackling_Estimation_Risk_Kelly_Options.pdf",
     "https://arxiv.org/pdf/2508.18868"),
]


def download_paper(name: str, url: str, download_dir: Path) -> tuple[str, bool, str]:
    """Download a single paper. Returns (name, success, message)."""
    filepath = download_dir / name
    if filepath.exists() and filepath.stat().st_size > 1000:
        return (name, True, "already exists")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"
    }

    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
            if resp.status_code == 200:
                content_type = resp.headers.get("Content-Type", "")
                # Verify it's actually a PDF
                if resp.content[:5] == b"%PDF-" or "pdf" in content_type.lower():
                    filepath.write_bytes(resp.content)
                    return (name, True, f"downloaded ({len(resp.content)//1024} KB)")
                else:
                    # Some SSRN links redirect to an abstract page
                    return (name, False, f"not a PDF (got {content_type[:50]})")
            elif resp.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            else:
                return (name, False, f"HTTP {resp.status_code}")
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
                continue
            return (name, False, str(e)[:80])

    return (name, False, "max retries exceeded")


def upload_to_s3(filepath: Path, s3_key: str, s3_client) -> tuple[str, bool, str]:
    """Upload a single file to S3. Returns (key, success, message)."""
    try:
        s3_client.upload_file(
            str(filepath),
            S3_BUCKET,
            s3_key,
            ExtraArgs={"ContentType": "application/pdf"}
        )
        return (s3_key, True, "uploaded")
    except Exception as e:
        return (s3_key, False, str(e)[:80])


def main():
    print("=" * 70)
    print("  Quant Trading Strategy Papers -> S3 Uploader")
    print(f"  Target: s3://{S3_BUCKET}/{S3_PREFIX}")
    print(f"  Total papers to process: {len(PAPERS)}")
    print("=" * 70)

    # Create download directory
    DOWNLOAD_DIR.mkdir(exist_ok=True)

    # ── Phase 1: Download all papers ──────────────────────────────────────
    print(f"\n📥 Phase 1: Downloading {len(PAPERS)} papers...\n")
    downloaded = []
    failed_downloads = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(download_paper, name, url, DOWNLOAD_DIR): name
            for name, url in PAPERS
        }
        for i, future in enumerate(as_completed(futures), 1):
            name, success, msg = future.result()
            status = "✅" if success else "❌"
            print(f"  [{i}/{len(PAPERS)}] {status} {name[:60]}... {msg}")
            if success:
                downloaded.append(name)
            else:
                failed_downloads.append((name, msg))

    print(f"\n  Downloaded: {len(downloaded)}/{len(PAPERS)}")
    if failed_downloads:
        print(f"  Failed: {len(failed_downloads)}")

    # ── Phase 2: Upload to S3 ─────────────────────────────────────────────
    print(f"\n📤 Phase 2: Uploading {len(downloaded)} papers to S3...\n")

    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )

    uploaded = []
    failed_uploads = []

    for i, name in enumerate(downloaded, 1):
        filepath = DOWNLOAD_DIR / name
        s3_key = S3_PREFIX + name
        key, success, msg = upload_to_s3(filepath, s3_key, s3_client)
        status = "✅" if success else "❌"
        print(f"  [{i}/{len(downloaded)}] {status} {name[:60]}... {msg}")
        if success:
            uploaded.append(name)
        else:
            failed_uploads.append((name, msg))

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"  Total papers in list:    {len(PAPERS)}")
    print(f"  Successfully downloaded: {len(downloaded)}")
    print(f"  Successfully uploaded:   {len(uploaded)}")
    print(f"  Failed downloads:        {len(failed_downloads)}")
    print(f"  Failed uploads:          {len(failed_uploads)}")
    print(f"\n  S3 location: s3://{S3_BUCKET}/{S3_PREFIX}")

    if failed_downloads:
        print("\n  ⚠️  Failed downloads:")
        for name, msg in failed_downloads:
            print(f"    - {name}: {msg}")

    if failed_uploads:
        print("\n  ⚠️  Failed uploads:")
        for name, msg in failed_uploads:
            print(f"    - {name}: {msg}")

    print("\n✨ Done!\n")


if __name__ == "__main__":
    main()