# Reindustrialization Newsletter

An AI-powered hedge fund analysis and reporting system with a focus on reindustrialization trends.

## Features

* Weekly reindustrialization trend analysis using Perplexity API
* Automated email reports distribution
* PostgreSQL integration for subscriber management
* Docker deployment support
* Scheduled execution (Mondays at 6 AM CST)
* Legal disclaimer clarifying non-investment advice status

## Prerequisites

* Python 3.11+
* Poetry
* PostgreSQL database
* SMTP server for email delivery

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/YIG-DAO/reindustrialization-newsletter.git
    cd reindustrialization-newsletter
    ```

2. Copy the environment file and configure your variables:

    ```bash
    cp .env.example .env
    ```

3. Install dependencies with Poetry:

    ```bash
    poetry install
    ```

## Database Setup

Create a table in your PostgreSQL database for subscribers:

```sql
CREATE TABLE subscribers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT true,
    subscription_type VARCHAR(50) DEFAULT 'reindustrialization',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## Docker Deployment

Build the Docker image:

```bash
docker build -t reindustrialization-newsletter .
```

Run the container, ensuring you provide the necessary environment variables (e.g., via an `.env` file):

```bash
docker run --rm --env-file .env reindustrialization-newsletter
```

Or pass variables directly:

```bash
docker run --rm \
  -e PERPLEXITY_API_KEY='your_key' \
  -e POSTGRES_DB='your_db' \
  -e POSTGRES_USER='your_user' \
  # ... other required variables
  reindustrialization-newsletter
```

To check the logs of a running container (replace `<container_id>` with the actual ID):

```bash
docker logs <container_id>
```

## Environment Variables

Required environment variables:

* `PERPLEXITY_API_KEY`: Your Perplexity API key
* `POSTGRES_*`: PostgreSQL connection details
* `SMTP_*`: Email server configuration
* `SENDER_EMAIL`: Sender email address
* `DOCKER_REGISTRY`: (Optional) Docker registry for image storage
* `TAG`: (Optional) Docker image tag

## Scheduling

The service runs automatically every Monday at 6 AM CST. The workflow:

1. Fetches latest reindustrialization trends
2. Retrieves active subscribers from PostgreSQL
3. Generates and sends personalized reports
4. Includes rate limiting (1 second between emails)

## Usage

### Run Commands

1. Analyze a single ticker:

    ```bash
    poetry run python src/main.py --ticker AAPL --show-reasoning
    ```

2. Run the complete workflow (process all tickers and send emails):

    ```bash
    poetry run python workflow.py
    ```

3. Generate report without sending emails:

    ```bash
    poetry run python -m src.tools.report
    ```

4. Send report to specific email(s):

    ```bash
    poetry run python -m src.tools.report --email user@example.com
    ```

5. Run in test mode:
    * Sends a test report to the default test email
    * Optionally, specify an email address to send the test report to

    ```bash
    poetry run python workflow.py --test
    poetry run python workflow.py --email user@example.com --test
    ```

### Email Configuration

To send emails, set these environment variables in your `.env` file:

```bash
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_username
SMTP_PASSWORD=your_password
SENDER_EMAIL=sender@example.com
```

### Report Features

The generated reports include:

* Reindustrialization trend analysis
* Fund holdings analysis with AI-driven insights
* Market impact analysis
* Single consolidated footer with contact information
* Legal disclaimer stating that content is for informational purposes only and not investment advice

## Development

To run locally for development:

```bash
./workflow.sh
```

## Monitoring

Monitor the service using standard Docker commands:

```bash
# List running containers
docker ps

# Check logs
docker logs <container_id>
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is proprietary and confidential. All rights reserved.
