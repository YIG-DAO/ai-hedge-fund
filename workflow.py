import json
import os
import sys
import logging
from datetime import datetime
import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from src.tools.db import get_subscriber_emails
from src.tools.report import send_email_report
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check required environment variables."""
    required_vars = [
        'PERPLEXITY_API_KEY',
        'POSTGRES_HOST',
        'POSTGRES_DB',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

def process_ticker(ticker):
    """Process a single ticker and return its analysis result."""
    try:
        import subprocess
        result = subprocess.run(
            ['poetry', 'run', 'python', 'src/main.py', '--ticker', ticker, '--show-reasoning'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Error analyzing {ticker}: {result.stderr}")
            return None
            
        # Extract the final result JSON block
        output_lines = result.stdout.split('\n')
        json_lines = []
        found_final = False
        for line in output_lines:
            if 'Final Result:' in line:
                found_final = True
                continue
            if found_final:
                json_lines.append(line)
        
        if not json_lines:
            logger.error(f"Error parsing JSON result for {ticker}")
            return None
            
        json_str = '\n'.join(json_lines)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.error(f"Error parsing JSON result for {ticker}")
            return None
            
    except Exception as e:
        logger.error(f"Error processing {ticker}: {str(e)}")
        return None

def distribute_reports():
    """Send reports to all subscribers."""
    try:
        emails = get_subscriber_emails()
        total = len(emails)
        logger.info(f'Starting distribution to {total} subscribers...')
        
        for i, email in enumerate(emails, 1):
            try:
                send_email_report([email])
                logger.info(f'Sent report to {email} ({i}/{total})')
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f'Failed to send to {email}: {e}')
        
        logger.info('Distribution completed!')
    except Exception as e:
        logger.error(f'Distribution error: {e}')

def run_analysis():
    """Main function to run the weekly analysis and distribution."""
    logger.info("Starting weekly reindustrialization report distribution...")
    
    try:
        # Check environment variables
        check_environment()
        
        # Read tickers from fund.json
        with open('fund.json', 'r') as f:
            fund_data = json.load(f)
            # Extract tickers from all categories
            tickers = []
            for category in fund_data['holdings'].values():
                tickers.extend(category['holdings'])
        
        # Process tickers and collect results
        results = {}
        successful = 0
        failed = 0
        
        for ticker in tickers:
            logger.info(f"Processing {ticker}...")
            result = process_ticker(ticker)
            
            if result:
                results[ticker] = result
                successful += 1
            else:
                failed += 1
        
        # Write results to fund_state.json
        with open('fund_state.json', 'w') as f:
            json.dump({"holdings": results}, f, indent=2)
        
        logger.info(f"Analysis complete. Results written to fund_state.json")
        logger.info(f"Successfully analyzed: {successful} tickers")
        logger.info(f"Failed analyses: {failed} tickers")
        
        # Distribute reports
        distribute_reports()
        
        logger.info("Weekly report distribution completed!")
        
    except Exception as e:
        logger.error(f"Error in analysis run: {e}")
        raise

def main():
    """Initialize and start the scheduler."""
    # Run analysis immediately at startup
    logger.info("Running initial analysis at startup...")
    run_analysis()
    
    scheduler = BlockingScheduler()
    
    # Schedule the job to run every Monday at 6 AM CST
    scheduler.add_job(
        run_analysis,
        trigger=CronTrigger(
            day_of_week='mon',
            hour=6,
            minute=0,
            timezone=pytz.timezone('America/Chicago')
        ),
        name='weekly_analysis',
        misfire_grace_time=3600  # Allow the job to be an hour late if system was down
    )
    
    try:
        logger.info("Starting scheduler...")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()

if __name__ == '__main__':
    main()
