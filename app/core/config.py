from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings - lightweight version without database."""
    
    # API Settings
    api_v1_str: str = "/api/v1"
    project_name: str = "Stock API V2"
    
    # Trading defaults
    initial_balance: float = 10000.0
    commission_rate: float = 0.001  # 0.1% per trade
    
    # Rate limiting for stock fetching
    rate_limit_delay: float = 0.1  # 100ms between requests
    max_workers: int = 20
    batch_size: int = 50
    
    class Config:
        env_file = ".env"


settings = Settings()

