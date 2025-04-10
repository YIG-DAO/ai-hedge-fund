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
            
            if agent_type and signal.get('signal') in ['bullish', 'bearish', 'neutral']:
                viz_data[agent_type][signal['signal']] += 1
    
    # Add current date/time for the report
    current_time = datetime.now()
    
    return {
        'fund_name': fund_config.get('fund_name', 'Reindustrialization Equity Fund'),
        'fund_config': fund_config,
        'holdings': holdings,
        'trends': trends,
        'viz_data': viz_data,
        'stats': {
            'total': total_holdings,
            'successful': successful_analyses,
            'failed': failed_analyses
        },
        'now': current_time  # Add current time to template data
    }

def render_html_report(trends: Dict[str, Any] = {}, template_name: str = 'report.html') -> str:
    """Render the HTML report using the inline template.
    
    Args:
        trends: Dictionary containing reindustrialization trends data
        template_name: Name of the template type to use ('report.html' or 'fund_report.html')
    """
    # Prepare template data
    template_data = prepare_template_data(trends)
    
    # Create a single HTML document
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Reindustrialization Newsletter</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --technical-color: #4BC0C0;
            --fundamental-color: #FF6384;
            --sentiment-color: #FFCE56;
            --valuation-color: #9966FF;
            --risk-color: #FF9F40;
            --score-color: #36A2EB;
            --bullish-color: #4CAF50;
            --neutral-color: #9E9E9E;
            --bearish-color: #F44336;
        }
        
        body { 
            font-family: Arial, sans-serif; 
            margin: 0;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #fff;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #eee;
            padding-bottom: 20px;
        }

        .header img {
            height: 50px;
            margin-bottom: 10px;
        }
        
        h1, h2, h3, h4 {
            text-align: center;
            color: #2c3e50;
            margin-bottom: 20px;
        }
        
        h1 {
            font-size: 28px;
            font-weight: 700;
        }
        
        h2 {
            font-size: 24px;
            margin-top: 30px;
        }
        
        h3 {
            font-size: 20px;
            margin-top: 25px;
        }

        .reindustrialization-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .highlights-list {
            list-style-type: none;
            padding: 0;
            margin: 0 auto;
            max-width: 90%;
        }
        
        .highlights-list li {
            margin: 15px 0;
            padding: 12px 15px;
            background: white;
            border-left: 4px solid var(--technical-color);
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }

        .holdings-analysis {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }

        .holdings-group {
            margin-bottom: 30px;
        }

        .holding-item {
            border: 1px solid #eee;
            padding: 20px;
            margin: 15px 0;
            border-radius: 6px;
            transition: all 0.3s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }

        .holding-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            border-bottom: 1px solid #f5f5f5;
            padding-bottom: 10px;
        }

        .holding-title {
            font-size: 1.4em;
            font-weight: bold;
        }

        .holding-action {
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: bold;
        }

        .action-buy { background: var(--bullish-color); color: white; }
        .action-sell { background: var(--bearish-color); color: white; }
        .action-hold { background: var(--neutral-color); color: white; }

        .signals-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }

        .signal-item {
            padding: 15px;
            border-radius: 6px;
            text-align: center;
            background-color: rgba(248, 249, 250, 0.7);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }

        .signal-name {
            font-weight: bold;
            margin-bottom: 8px;
            color: #2c3e50;
        }

        .signal-value {
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.95em;
        }

        .signal-dot {
            width: 12px;
            height: 12px;
            margin-right: 8px;
            border-radius: 50%;
        }

        /* Analysis type colors */
        .technical { background-color: var(--technical-color); }
        .fundamental { background-color: var(--fundamental-color); }
        .sentiment { background-color: var(--sentiment-color); }
        .valuation { background-color: var(--valuation-color); }
        .risk { background-color: var(--risk-color); }
        .score { background-color: var(--score-color); }
        
        /* Signal indicators */
        .bullish { background-color: var(--bullish-color); }
        .neutral { background-color: var(--neutral-color); }
        .bearish { background-color: var(--bearish-color); }
        .hold { background-color: var(--neutral-color); }

        .reasoning-block {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            margin-top: 15px;
            border-left: 3px solid #ddd;
            line-height: 1.5;
        }
        
        .reasoning-block strong {
            color: #2c3e50;
        }

        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
        }

        .legend-section h3 {
            margin-bottom: 15px;
        }

        .legend-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin: 0 auto;
            max-width: 90%;
        }

        .legend-item {
            display: flex;
            align-items: center;
            padding: 12px;
            background: white;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .legend-color {
            width: 20px;
            height: 20px;
            margin-right: 10px;
            border-radius: 50%;
        }
        
        /* Footer styles */
        .footer-title {
            font-size: 1.2em;
            font-weight: bold;
            text-align: center;
            margin: 15px 0 5px;
        }

        .footer-subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 15px;
            font-size: 0.9em;
        }

        .footer-contact {
            text-align: center;
            margin: 20px 0;
        }
        
        .footer-contact a {
            color: #3498db;
            text-decoration: none;
        }
        
        .footer-contact a:hover {
            text-decoration: underline;
        }
        
        /* Signal colors for direct reference */
        .bullish-dot { background-color: var(--bullish-color); }
        .neutral-dot { background-color: var(--neutral-color); }
        .bearish-dot { background-color: var(--bearish-color); }
        
        /* Table styling */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }

        th {
            background-color: #f8f9fa;
            font-weight: bold;
            color: #2c3e50;
        }
        
        tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        
        tr:hover {
            background-color: #f1f5f9;
        }
    </style>
</head>
<body>
    <div class="container">
"""
    
    # Choose the content type based on template_name
    if template_name == 'report.html':
        # Generate main newsletter content
        main_content = """
        <div class="header">
            <img src="https://yeetum.com/favicon.ico" alt="Yeetum Logo">
            <h1>Weekly Reindustrialization Newsletter</h1>
        </div>

        <!-- Reindustrialization Section -->
        <div class="reindustrialization-section">
            <h2>Bottom Line Up Front</h2>
            <p>{summary}</p>
            
            <h3>Key Highlights</h3>
            <ul class="highlights-list">
                {highlights}
            </ul>
        </div>

        <div class="header">
            <h1>{fund_name} Holdings Analysis</h1>
        </div>

        <div class="holdings-analysis">
            <div class="holdings-group">
                {holdings}
            </div>
        </div>
"""
        
        # Format highlights
        highlights_html = ""
        for highlight in trends.get('highlights', ['No highlights available']):
            highlights_html += f"<li>{highlight}</li>"
        
        # Format holdings
        holdings_html = ""
        for ticker, data in template_data['holdings'].items():
            # Create signals HTML
            signals_html = ""
            for signal in data.get('agent_signals', []):
                agent_name = signal.get('agent_name', signal.get('agent', 'Analysis'))
                signal_value = signal.get('signal', 'neutral')
                confidence = signal.get('confidence', 0)
                
                # Format confidence as percentage
                if isinstance(confidence, str) and '%' in confidence:
                    confidence_str = confidence
                else:
                    try:
                        conf_value = float(confidence) * 100
                        confidence_str = f"{conf_value:.0f}%"
                    except:
                        confidence_str = "N/A"
                
                signals_html += f"""
                <div class="signal-item">
                    <div class="signal-name">{agent_name}</div>
                    <div class="signal-value">
                        <span class="signal-dot {signal_value}"></span>
                        {signal_value} ({confidence_str})
                    </div>
                </div>
                """
            
            # Add holding item
            holdings_html += f"""
            <div class="holding-item">
                <div class="holding-header">
                    <div class="holding-title">{ticker}</div>
                    <div class="holding-action action-{data.get('action', 'hold')}">{data.get('action', 'HOLD').upper()}</div>
                </div>
                
                <div class="signals-grid">
                    {signals_html}
                </div>
                
                <div class="reasoning-block">
                    <p><strong>Reasoning:</strong> {data.get('reasoning', 'No reasoning available')}</p>
                </div>
            </div>
            """
        
        # Format the main content
        content = main_content.format(
            summary=trends.get('summary', 'Trends data currently unavailable'),
            highlights=highlights_html,
            fund_name=template_data['fund_name'],
            holdings=holdings_html
        )
    else:
        # Fund report content
        content = """
        <div class="footer">
            <img src="https://yeetum.com/favicon.ico" alt="Logo" style="height: 40px; margin: 15px auto; display: block;">
            <div class="footer-title">Yeetum Intelligence Platform</div>
            <div class="footer-subtitle">Equities Analysis Service</div>
            <div class="footer-contact">
                Contact for custom analysis @ <a href="https://yeetum.com/contact">yeetum.com/contact</a>
            </div>
            <p style="text-align: center; font-size: 0.8em; color: #666;">Report Date: {date}</p>
            <div class="disclaimer" style="text-align: center; font-size: 0.8em; color: #666; margin-top: 10px; padding: 10px; border-top: 1px solid #eee;">
                <strong>DISCLAIMER:</strong> This is not investment advice. Yeetum provides information services and acts as information advisors tracking cyber financial intelligence for data science purposes only.
            </div>
        </div>
        """.format(
            date=template_data['now'].strftime('%Y-%m-%d %H:%M:%S')
        )
    
    # Complete the HTML
    closing_html = """
    </div>
</body>
</html>"""

    return html_content + content + closing_html

def send_email_report(recipients: List[str], trends: Dict[str, Any] = None) -> None:
    """Send the HTML report via email.
    
    Args:
        recipients: List of email addresses to send the report to
        trends: Optional pre-fetched reindustrialization trends data. If not provided, will fetch from API.
    """
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
    
    # Get reindustrialization trends if not provided
    if trends is None:
        try:
            trends = get_reindustrialization_trends()
        except Exception as e:
            print(f"Warning: Failed to fetch reindustrialization trends: {e}")
            trends = {
                'summary': 'American manufacturing continues to show resilience despite global economic headwinds.',
                'highlights': [
                    "Recent data indicates steady investment in domestic production capacity.",
                    "CHIPS Act and Inflation Reduction Act continue to drive capital allocation toward strategic industries."
                ]
            }
    
    # Prepare template data
    template_data = prepare_template_data(trends)
    
    # Generate main newsletter content
    main_content = """
        <div class="header">
            <img src="https://yeetum.com/favicon.ico" alt="Yeetum Logo">
            <h1>Weekly Reindustrialization Newsletter</h1>
        </div>

        <!-- Reindustrialization Section -->
        <div class="reindustrialization-section">
            <h2>Bottom Line Up Front</h2>
            <p>{summary}</p>
            
            <h3>Key Highlights</h3>
            <ul class="highlights-list">
                {highlights}
            </ul>
        </div>

        <div class="header">
            <h1>{fund_name} Holdings Analysis</h1>
        </div>

        <div class="holdings-analysis">
            <div class="holdings-group">
                {holdings}
            </div>
        </div>
"""
    
    # Format highlights
    highlights_html = ""
    for highlight in trends.get('highlights', ['No highlights available']):
        highlights_html += f"<li>{highlight}</li>"
    
    # Format holdings
    holdings_html = ""
    for ticker, data in template_data['holdings'].items():
        # Create signals HTML
        signals_html = ""
        for signal in data.get('agent_signals', []):
            agent_name = signal.get('agent_name', signal.get('agent', 'Analysis'))
            signal_value = signal.get('signal', 'neutral')
            confidence = signal.get('confidence', 0)
            
            # Format confidence as percentage
            if isinstance(confidence, str) and '%' in confidence:
                confidence_str = confidence
            else:
                try:
                    conf_value = float(confidence) * 100
                    confidence_str = f"{conf_value:.0f}%"
                except:
                    confidence_str = "N/A"
            
            signals_html += f"""
            <div class="signal-item">
                <div class="signal-name">{agent_name}</div>
                <div class="signal-value">
                    <span class="signal-dot {signal_value}"></span>
                    {signal_value} ({confidence_str})
                </div>
            </div>
            """
        
        # Add holding item
        holdings_html += f"""
        <div class="holding-item">
            <div class="holding-header">
                <div class="holding-title">{ticker}</div>
                <div class="holding-action action-{data.get('action', 'hold')}">{data.get('action', 'HOLD').upper()}</div>
            </div>
            
            <div class="signals-grid">
                {signals_html}
            </div>
            
            <div class="reasoning-block">
                <p><strong>Reasoning:</strong> {data.get('reasoning', 'No reasoning available')}</p>
            </div>
        </div>
        """
    
    # Format the main content
    formatted_main = main_content.format(
        summary=trends.get('summary', 'Trends data currently unavailable'),
        highlights=highlights_html,
        fund_name=template_data['fund_name'],
        holdings=holdings_html
    )
    
    # Generate fund report content (simplified for this email)
    fund_content = """
        <div class="footer">
            <img src="https://yeetum.com/favicon.ico" alt="Logo" style="height: 40px; margin: 15px auto; display: block;">
            <div class="footer-title">Yeetum Intelligence Platform</div>
            <div class="footer-subtitle">Equities Analysis Service</div>
            <div class="footer-contact">
                Contact for custom analysis @ <a href="https://yeetum.com/contact">yeetum.com/contact</a>
            </div>
            <p style="text-align: center; font-size: 0.8em; color: #666;">Report Date: {date}</p>
            <div class="disclaimer" style="text-align: center; font-size: 0.8em; color: #666; margin-top: 10px; padding: 10px; border-top: 1px solid #eee;">
                <strong>DISCLAIMER:</strong> This is not investment advice. Yeetum provides information services and acts as information advisors tracking cyber financial intelligence for data science purposes only.
            </div>
        </div>
    """.format(
        date=template_data['now'].strftime('%Y-%m-%d %H:%M:%S')
    )
    
    # Complete the HTML
    closing_html = """
    </div>
</body>
</html>"""

    # Combine reports with proper sections
    combined_report = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Reindustrialization Newsletter</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --technical-color: #4BC0C0;
            --fundamental-color: #FF6384;
            --sentiment-color: #FFCE56;
            --valuation-color: #9966FF;
            --risk-color: #FF9F40;
            --score-color: #36A2EB;
            --bullish-color: #4CAF50;
            --neutral-color: #9E9E9E;
            --bearish-color: #F44336;
        }
        
        body { 
            font-family: Arial, sans-serif; 
            margin: 0;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #fff;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #eee;
            padding-bottom: 20px;
        }

        .header img {
            height: 50px;
            margin-bottom: 10px;
        }
        
        h1, h2, h3, h4 {
            text-align: center;
            color: #2c3e50;
            margin-bottom: 20px;
        }
        
        h1 {
            font-size: 28px;
            font-weight: 700;
        }
        
        h2 {
            font-size: 24px;
            margin-top: 30px;
        }
        
        h3 {
            font-size: 20px;
            margin-top: 25px;
        }

        .reindustrialization-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .highlights-list {
            list-style-type: none;
            padding: 0;
            margin: 0 auto;
            max-width: 90%;
        }
        
        .highlights-list li {
            margin: 15px 0;
            padding: 12px 15px;
            background: white;
            border-left: 4px solid var(--technical-color);
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }

        .holdings-analysis {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }

        .holdings-group {
            margin-bottom: 30px;
        }

        .holding-item {
            border: 1px solid #eee;
            padding: 20px;
            margin: 15px 0;
            border-radius: 6px;
            transition: all 0.3s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }

        .holding-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            border-bottom: 1px solid #f5f5f5;
            padding-bottom: 10px;
        }

        .holding-title {
            font-size: 1.4em;
            font-weight: bold;
        }

        .holding-action {
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: bold;
        }

        .action-buy { background: var(--bullish-color); color: white; }
        .action-sell { background: var(--bearish-color); color: white; }
        .action-hold { background: var(--neutral-color); color: white; }

        .signals-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }

        .signal-item {
            padding: 15px;
            border-radius: 6px;
            text-align: center;
            background-color: rgba(248, 249, 250, 0.7);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }

        .signal-name {
            font-weight: bold;
            margin-bottom: 8px;
            color: #2c3e50;
        }

        .signal-value {
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.95em;
        }

        .signal-dot {
            width: 12px;
            height: 12px;
            margin-right: 8px;
            border-radius: 50%;
        }

        /* Analysis type colors */
        .technical { background-color: var(--technical-color); }
        .fundamental { background-color: var(--fundamental-color); }
        .sentiment { background-color: var(--sentiment-color); }
        .valuation { background-color: var(--valuation-color); }
        .risk { background-color: var(--risk-color); }
        .score { background-color: var(--score-color); }
        
        /* Signal indicators */
        .bullish { background-color: var(--bullish-color); }
        .neutral { background-color: var(--neutral-color); }
        .bearish { background-color: var(--bearish-color); }
        .hold { background-color: var(--neutral-color); }

        .reasoning-block {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            margin-top: 15px;
            border-left: 3px solid #ddd;
            line-height: 1.5;
        }
        
        .reasoning-block strong {
            color: #2c3e50;
        }

        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
        }

        .legend-section h3 {
            margin-bottom: 15px;
        }

        .legend-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin: 0 auto;
            max-width: 90%;
        }

        .legend-item {
            display: flex;
            align-items: center;
            padding: 12px;
            background: white;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .legend-color {
            width: 20px;
            height: 20px;
            margin-right: 10px;
            border-radius: 50%;
        }
        
        /* Footer styles */
        .footer-title {
            font-size: 1.2em;
            font-weight: bold;
            text-align: center;
            margin: 15px 0 5px;
        }

        .footer-subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 15px;
            font-size: 0.9em;
        }

        .footer-contact {
            text-align: center;
            margin: 20px 0;
        }
        
        .footer-contact a {
            color: #3498db;
            text-decoration: none;
        }
        
        .footer-contact a:hover {
            text-decoration: underline;
        }
        
        /* Signal colors for direct reference */
        .bullish-dot { background-color: var(--bullish-color); }
        .neutral-dot { background-color: var(--neutral-color); }
        .bearish-dot { background-color: var(--bearish-color); }
        
        /* Table styling */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }

        th {
            background-color: #f8f9fa;
            font-weight: bold;
            color: #2c3e50;
        }
        
        tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        
        tr:hover {
            background-color: #f1f5f9;
        }
    </style>
</head>
<body>
    <div class="container">
"""
    
    combined_report += formatted_main + """
    <div style="border-top: 2px solid #eee; margin: 30px 0;"></div>
    """ + fund_content + closing_html
    
    for recipient in recipients:
        msg['Subject'] = f"Weekly Reindustrialization Newsletter - {template_data['now'].strftime('%B %d, %Y')}"
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
    # Get reindustrialization trends
    try:
        trends = get_reindustrialization_trends()
    except Exception as e:
        print(f"Warning: Failed to fetch reindustrialization trends: {e}")
        trends = {
            'summary': 'American manufacturing continues to show resilience despite global economic headwinds.',
            'highlights': [
                "Recent data indicates steady investment in domestic production capacity.",
                "CHIPS Act and Inflation Reduction Act continue to drive capital allocation toward strategic industries."
            ]
        }
        
    # Generate report HTML content
    html_content = render_html_report(trends)
    
    # Create reports directory if it doesn't exist
    Path('reports').mkdir(exist_ok=True)
    
    # Save to file
    output_path = Path('reports/fund_report.html')
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
