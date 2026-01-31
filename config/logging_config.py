from loguru import logger

# Configure loguru for structured, colored logs
logger.remove()  # Remove default handler
logger.add(
    "logs/app.log",  # Log to file
    rotation="10 MB",  # Rotate when file reaches 10MB
    retention="1 week",  # Keep logs for 1 week
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    serialize=True,  # JSON format for structured logs
    backtrace=True,
    diagnose=True,
)
logger.add(
    lambda msg: print(msg, end=""),  # Also print to console with colors
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}:{function}:{line}</cyan> | <level>{message}</level>",
    colorize=True,
)

# Export the logger
__all__ = ["logger"]