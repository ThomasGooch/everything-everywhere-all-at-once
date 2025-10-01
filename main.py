"""Main entry point for the AI Development Orchestrator"""

import asyncio
import logging
import sys
from pathlib import Path

from core import AgentContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main application entry point"""
    try:
        # Initialize AgentContext with configuration
        config_dir = Path("config")
        
        async with AgentContext(config_dir).managed_context() as agent_context:
            logger.info("🚀 AI Development Orchestrator started successfully")
            
            # Display system information
            system_info = agent_context.get_system_info()
            logger.info(f"System Info: {system_info}")
            
            # Perform health check
            health_status = await agent_context.health_check()
            logger.info(f"Health Status: {health_status['overall_status']}")
            
            if health_status["plugins"]:
                logger.info("Plugin Status:")
                for plugin_id, status in health_status["plugins"].items():
                    logger.info(f"  {plugin_id}: {status}")
            
            # Keep the application running
            logger.info("System running. Press Ctrl+C to stop...")
            try:
                while True:
                    await asyncio.sleep(10)
                    
                    # Periodic health check
                    health = await agent_context.health_check()
                    if health["overall_status"] != "healthy":
                        logger.warning(f"Health status: {health['overall_status']}")
                        
            except KeyboardInterrupt:
                logger.info("Shutdown requested by user")
                
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())