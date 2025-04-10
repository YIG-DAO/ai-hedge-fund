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
import argparse

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

def distribute_reports(test_email=None):
    """Send reports to all subscribers.
    
    Args:
        test_email: If provided, sends only to this email address (test mode)
    """
    try:
        # Fetch reindustrialization trends once for all emails
        try:
            from src.tools.perplexity_client import get_reindustrialization_trends
            logger.info("Fetching reindustrialization trends...")
            trends = get_reindustrialization_trends()
            logger.info("Successfully fetched reindustrialization trends")
        except Exception as e:
            logger.error(f"Error fetching reindustrialization trends: {e}")
            # Fallback trends data
            trends = {
                'summary': 'American manufacturing continues to show resilience despite global economic headwinds.',
                'highlights': [
                    "Recent data indicates steady investment in domestic production capacity.",
                    "CHIPS Act and Inflation Reduction Act continue to drive capital allocation toward strategic industries."
                ]
            }
            
        if test_email:
            # Test mode - send only to specified email
            logger.info(f'TEST MODE: Sending report only to {test_email}')
            from src.tools.report import send_email_report
            send_email_report([test_email], trends)
            logger.info(f'TEST MODE: Sent report to {test_email}')
            return
            
        # Normal distribution mode
        emails = get_subscriber_emails()
        total = len(emails)
        logger.info(f'Starting distribution to {total} subscribers...')
        
        from src.tools.report import send_email_report
        for i, email in enumerate(emails, 1):
            try:
                send_email_report([email], trends)
                logger.info(f'Sent report to {email} ({i}/{total})')
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f'Failed to send to {email}: {e}')
        
        logger.info('Distribution completed!')
    except Exception as e:
        logger.error(f'Distribution error: {e}')

def run_analysis(test_email=None):
    """Main function to run the weekly analysis and distribution.
    
    Args:
        test_email: If provided, runs in test mode sending only to this email
    """
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
        distribute_reports(test_email)
        
        logger.info("Weekly report distribution completed!")
        
    except Exception as e:
        logger.error(f"Error in analysis run: {e}")
        raise

def main():
    """Initialize and start the scheduler."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run reindustrialization newsletter workflow')
    parser.add_argument('--email', type=str, help='Email address for test mode (sends only to this address)')
    parser.add_argument('--test', action='store_true', help='Run in test mode (alternative to --email)')
    args = parser.parse_args()
    
    # Determine test email (if any)
    test_email = None
    if args.email:
        test_email = args.email
    elif args.test:
        test_email = "tobalo@yeetum.com"  # Default test email
        
    if test_email:
        # Run once in test mode
        logger.info(f"Running in TEST MODE for {test_email}")
        run_analysis(test_email)
    else:
        # Run normally with scheduler
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
