# AI Hedge Fund

An AI-powered hedge fund analysis and reporting system with a focus on reindustrialization trends.

## Features

- Weekly reindustrialization trend analysis using Perplexity API
- Automated email reports distribution
- PostgreSQL integration for subscriber management
- Docker Swarm deployment support
- Scheduled execution (Mondays at 6 AM CST)

## Prerequisites

- Python 3.11+
- Docker and Docker Swarm
- PostgreSQL database
- SMTP server for email delivery

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YIG-DAO/ai-hedge-fund.git
cd ai-hedge-fund
```

2. Copy the environment file and configure your variables:
```bash
cp .env.example .env
```

3. Install dependencies:
```bash
pip install -r requirements.txt
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

1. Initialize Docker Swarm (if not already done):
```bash
docker swarm init
```

2. Deploy the stack:
```bash
docker stack deploy -c docker-compose.yml reindustrialization
```

3. Check service status:
```bash
docker service ls
docker service logs reindustrialization_reindustrialization-report
```

## Environment Variables

Required environment variables:

- `PERPLEXITY_API_KEY`: Your Perplexity API key
- `POSTGRES_*`: PostgreSQL connection details
- `SMTP_*`: Email server configuration
- `SENDER_EMAIL`: Sender email address
- `DOCKER_REGISTRY`: (Optional) Docker registry for image storage
- `TAG`: (Optional) Docker image tag

## Scheduling

The service runs automatically every Monday at 6 AM CST. The workflow:

1. Fetches latest reindustrialization trends
2. Retrieves active subscribers from PostgreSQL
3. Generates and sends personalized reports
4. Includes rate limiting (1 second between emails)

## Development

To run locally for development:

```bash
./workflow.sh
```

## Monitoring

Monitor the service using Docker Swarm commands:

```bash
# View service status
docker service ls

# Check logs
docker service logs reindustrialization_reindustrialization-report

# Scale service
docker service scale reindustrialization_reindustrialization-report=N
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is proprietary and confidential. All rights reserved.
