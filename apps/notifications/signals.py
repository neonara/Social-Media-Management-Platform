import logging
from django.core.cache import cache
from django.conf import settings
from redis.exceptions import ConnectionError

logger = logging.getLogger(__name__)

def check_cache_connection(sender, **kwargs):
    """
    Check if Redis cache connection is working properly
    And verify any critical cache values
    """
    logger.info("Checking Redis cache connection...")
    
    try:
        # Try to ping Redis
        if hasattr(cache, 'ping'):
            cache.ping()
            logger.info("✓ Redis connection successful")
        
        # Test setting and getting a value
        test_key = "cache_connection_test"
        test_value = "working"
        cache.set(test_key, test_value, 60)
        retrieved = cache.get(test_key)
        
        if retrieved == test_value:
            logger.info("✓ Redis cache read/write test successful")
        else:
            logger.warning("⚠ Redis cache read/write test failed")
            
        # Clean up test key
        cache.delete(test_key)
        
    except ConnectionError as e:
        logger.error(f"❌ Redis connection error: {str(e)}")
        logger.error(f"❌ Redis connection URL: {settings.CACHES['default']['LOCATION']}")
        logger.error("❌ Please make sure Redis is running and the connection settings are correct")
        
    except Exception as e:
        logger.error(f"❌ Cache initialization error: {str(e)}")