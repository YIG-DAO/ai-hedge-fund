import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import jinja2
from .perplexity_client import get_reindustrialization_trends

def load_fund_state() -> Dict[str, Any]:
    """Load the fund state from JSON file."""
    with open('fund_state.json', 'r') as f:
        return json.load(f)

def load_fund_config() -> Dict[str, Any]:
    """Load the fund configuration."""
    with open('fund.json', 'r') as f:
        return json.load(f)

def format_confidence(confidence: float) -> str:
    """Format confidence as percentage."""
    return f"{confidence * 100:.1f}%"

def get_signal_class(action: str) -> str:
    """Get CSS class based on action."""
    if action == "buy":
        return "bullish"
    elif action == "sell":
        return "bearish"
    return "neutral"

def get_confidence_class(confidence: float) -> str:
    """Get CSS class based on confidence level."""
    if confidence >= 0.8:
        return "confidence-high"
    return ""

def prepare_visualization_data(fund_config: Dict[str, Any], fund_state: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare data for visualizations."""
    sector_counts = {}
    action_counts = {'buy': 0, 'sell': 0, 'hold': 0}
    sentiment_by_sector = {}
    
    for category, data in fund_config['holdings'].items():
        sector_name = data['name']
        sector_counts[sector_name] = len(data['holdings'])
        sentiment_by_sector[sector_name] = {'bullish': 0, 'bearish': 0, 'neutral': 0}
        
        for ticker in data['holdings']:
            if ticker in fund_state['holdings']:
                action = fund_state['holdings'][ticker].get('action', 'hold')
                action_counts[action] += 1
                
                # Count sentiment signals for each sector
                signals = fund_state['holdings'][ticker].get('agent_signals', [])
                for signal in signals:
                    if signal.get('signal') in ['bullish', 'bearish', 'neutral']:
                        sentiment_by_sector[sector_name][signal['signal']] += 1
    
    return {
        'sector_distribution': {
            'labels': list(sector_counts.keys()),
            'data': list(sector_counts.values())
        },
        'position_actions': {
            'labels': list(action_counts.keys()),
            'data': list(action_counts.values())
        },
        'sector_sentiment': {
            'sectors': list(sentiment_by_sector.keys()),
            'bullish': [data['bullish'] for data in sentiment_by_sector.values()],
            'bearish': [data['bearish'] for data in sentiment_by_sector.values()],
            'neutral': [data['neutral'] for data in sentiment_by_sector.values()]
        }
    }

def prepare_template_data(trends: Dict[str, Any] = {}) -> Dict[str, Any]:
    """Prepare data for the HTML template."""
    fund_state = load_fund_state()
    fund_config = load_fund_config()
    
    # Get holdings data
    holdings = fund_state.get('holdings', {})
    
    # Count analyses
    total_holdings = len(holdings)
    successful_analyses = sum(1 for h in holdings.values() if h.get('action') != 'error')
    failed_analyses = total_holdings - successful_analyses
    
    # Prepare visualization data
    viz_data = {
        'technical': {'bullish': 0, 'bearish': 0, 'neutral': 0},
        'fundamental': {'bullish': 0, 'bearish': 0, 'neutral': 0},
        'sentiment': {'bullish': 0, 'bearish': 0, 'neutral': 0},
        'valuation': {'bullish': 0, 'bearish': 0, 'neutral': 0},
    }
    
    # Process holdings data
    for holding_data in holdings.values():
        for signal in holding_data.get('agent_signals', []):
            agent_name = signal.get('agent', signal.get('agent_name', '')).lower()
            if not agent_name:
                continue
                
            # Extract the type of analysis from the agent name
            agent_type = None
            for key in viz_data.keys():
                if key in agent_name:
                    agent_type = key
                    break
                    
            if agent_type:
                signal_type = signal.get('signal', 'neutral').lower()
                viz_data[agent_type][signal_type] = viz_data[agent_type].get(signal_type, 0) + 1
    
    return {
        'fund_name': fund_config.get('fund_name', 'AI Hedge Fund'),
        'holdings': holdings,
        'successful_analyses': successful_analyses,
        'failed_analyses': failed_analyses,
        'total_holdings': total_holdings,
        'visualizations': viz_data,
        'trends': trends,
        'date': datetime.now().strftime('%Y-%m-%d')
    }

def render_html_report(trends: Dict[str, Any] = {}, template_name: str = 'report.html') -> str:
    """Render the HTML report using the template.
    
    Args:
        trends: Dictionary containing reindustrialization trends data
        template_name: Name of the template to use (report.html or fund_report.html)
    """
    template_path = Path(f'public/{template_name}')
    with open(template_path, 'r') as f:
        template_str = f.read()
    
    env = jinja2.Environment(
        loader=jinja2.BaseLoader(),
        autoescape=jinja2.select_autoescape(['html', 'xml']),
        trim_blocks=True,
        lstrip_blocks=True,
        variable_start_string='{{',
        variable_end_string='}}',
        block_start_string='{%',
        block_end_string='%}'
    )
    
    template = env.from_string(template_str)
    template_data = prepare_template_data(trends)
    return template.render(**template_data)

def send_email_report(recipients: List[str]) -> None:
    """Send the HTML report via email."""
    # Load environment variables from .env file if dotenv is available
    try:
        import dotenv
        dotenv.load_dotenv()
    except ImportError:
        pass
        
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    sender_email = os.getenv('SENDER_EMAIL') or os.getenv('SMTP_SENDER')
    
    if not all([smtp_server, smtp_username, smtp_password, sender_email]):
        raise ValueError("Missing required email configuration in environment variables")
    
    # Create message
    msg = MIMEMultipart('alternative')
    fund_config = load_fund_config()
    
    # Get reindustrialization trends
    try:
        trends = get_reindustrialization_trends()
    except Exception as e:
        print(f"Warning: Failed to fetch reindustrialization trends: {e}")
        trends = {
            'summary': 'Reindustrialization trends data temporarily unavailable',
            'highlights': ['Data fetch error - please check system logs']
        }
    
    # Generate the report only once and store it in a variable
    main_report = render_html_report(trends, 'report.html')
    fund_report = render_html_report(trends, 'fund_report.html')
    
    # Combine reports with a separator
    combined_report = f"""
    <div style="margin-bottom: 50px;">
        {main_report}
    </div>
    <div style="border-top: 2px solid #eee; margin: 30px 0;"></div>
    <div>
        {fund_report}
    </div>
    """
    
    for recipient in recipients:
        msg['Subject'] = f"Weekly Reindustrialization Newsletter - {datetime.now().strftime('%m/%d/%Y')}"
        msg['From'] = sender_email
        msg['To'] = recipient
        
        msg.attach(MIMEText(combined_report, 'html'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        print(f"Report sent to: {recipient}")

def generate_report() -> None:
    """Generate the HTML report and save it to a file."""
    html_content = render_html_report()
    output_path = Path('public/fund_report.html')
    with open(output_path, 'w') as f:
        f.write(html_content)
    print(f"Report generated: {output_path}")

if __name__ == '__main__':
    import sys
    # Load environment variables early
    try:
        import dotenv
        dotenv.load_dotenv()
        print("Loaded environment variables from .env")
    except ImportError:
        print("Warning: python-dotenv not found, environment variables must be set manually")
        
    if len(sys.argv) > 1 and sys.argv[1] == '--email':
        recipients = sys.argv[2:]
        if not recipients:
            print("Error: No email recipients provided")
            sys.exit(1)
        print(f"Sending email to: {', '.join(recipients)}")
        send_email_report(recipients)
    else:
        generate_report()
