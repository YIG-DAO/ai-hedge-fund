import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import jinja2

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

def prepare_template_data() -> Dict[str, Any]:
    """Prepare data for the HTML template."""
    fund_state = load_fund_state()
    fund_config = load_fund_config()
    
    holdings_groups = []
    successful_analyses = 0
    failed_analyses = 0
    total_holdings = 0
    
    # Prepare visualization data
    viz_data = prepare_visualization_data(fund_config, fund_state)
    
    for category, data in fund_config['holdings'].items():
        holdings = []
        for ticker in data['holdings']:
            total_holdings += 1
            if ticker in fund_state['holdings']:
                successful_analyses += 1
                holding_data = fund_state['holdings'][ticker]
                # Process agent signals
                agent_signals = holding_data.get('agent_signals', [])
                signals = {
                    'technical': {'signal': 'N/A', 'confidence': 0},
                    'fundamental': {'signal': 'N/A', 'confidence': 0},
                    'sentiment': {'signal': 'N/A', 'confidence': 0},
                    'valuation': {'signal': 'N/A', 'confidence': 0}
                }
                
                for signal in agent_signals:
                    agent = signal.get('agent', signal.get('agent_name', '')).lower()
                    if 'technical' in agent:
                        signals['technical'] = {'signal': signal['signal'], 'confidence': signal['confidence']}
                    elif 'fundamental' in agent:
                        signals['fundamental'] = {'signal': signal['signal'], 'confidence': signal['confidence']}
                    elif 'sentiment' in agent:
                        signals['sentiment'] = {'signal': signal['signal'], 'confidence': signal['confidence']}
                    elif 'valuation' in agent:
                        signals['valuation'] = {'signal': signal['signal'], 'confidence': signal['confidence']}

                # Process reasoning into bullet points
                reasoning_text = holding_data.get('reasoning', 'No reasoning available')
                reasoning_points = [point.strip() for point in reasoning_text.split('.') if point.strip()]

                holdings.append({
                    'ticker': ticker,
                    'action': holding_data.get('action', 'N/A'),
                    'confidence': format_confidence(holding_data.get('confidence', 0)),
                    'technical_signal': signals['technical']['signal'],
                    'technical_signal_class': signals['technical']['signal'],
                    'fundamental_signal': signals['fundamental']['signal'],
                    'fundamental_signal_class': signals['fundamental']['signal'],
                    'sentiment_signal': signals['sentiment']['signal'],
                    'sentiment_signal_class': signals['sentiment']['signal'],
                    'valuation_signal': signals['valuation']['signal'],
                    'valuation_signal_class': signals['valuation']['signal'],
                    'reasoning_points': reasoning_points,
                    'signal_class': get_signal_class(holding_data.get('action', '')),
                    'confidence_class': get_confidence_class(holding_data.get('confidence', 0))
                })
            else:
                failed_analyses += 1
        
        if holdings:
            holdings_groups.append({
                'name': data['name'],
                'holdings': holdings
            })
    
    return {
        'fund_name': fund_config['fund_name'],
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'holdings_groups': holdings_groups,
        'successful_analyses': successful_analyses,
        'failed_analyses': failed_analyses,
        'total_holdings': total_holdings,
        'visualizations': viz_data
    }

def render_html_report() -> str:
    """Render the HTML report using the template."""
    template_path = Path('public/report.html')
    with open(template_path, 'r') as f:
        template_str = f.read()
    
    # Create Jinja2 environment with custom delimiters to avoid conflicts
    env = jinja2.Environment(
        loader=jinja2.BaseLoader(),
        variable_start_string='{{',
        variable_end_string='}}',
        block_start_string='{{#',
        block_end_string='#}}',
    )
    
    template = env.from_string(template_str)
    return template.render(**prepare_template_data())

def send_email_report(recipients: List[str]) -> None:
    """Send the HTML report via email."""
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    sender_email = os.getenv('SENDER_EMAIL')
    
    if not all([smtp_server, smtp_username, smtp_password, sender_email]):
        raise ValueError("Missing required email configuration in environment variables")
    
    # Create message
    msg = MIMEMultipart('alternative')
    fund_config = load_fund_config()
    msg['Subject'] = f"{fund_config['fund_name']} Holdings Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    msg['From'] = sender_email
    msg['To'] = ', '.join(recipients)
    
    # Attach HTML report
    html_content = render_html_report()
    msg.attach(MIMEText(html_content, 'html'))
    
    # Send email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)

def generate_report() -> None:
    """Generate the HTML report and save it to a file."""
    html_content = render_html_report()
    output_path = Path('public/fund_report.html')
    with open(output_path, 'w') as f:
        f.write(html_content)
    print(f"Report generated: {output_path}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--email':
        recipients = sys.argv[2:]
        if not recipients:
            print("Error: No email recipients provided")
            sys.exit(1)
        send_email_report(recipients)
        print(f"Report sent to: {', '.join(recipients)}")
    else:
        generate_report()
