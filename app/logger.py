
import sys

import asyncio
from datetime import datetime
from typing import Any

from loguru import logger as loguru_logger

class AppLogger:
    def __init__(
        self,
        log_file: str = None,
        log_level: str = "DEBUG",
        rotation: str = "1 day",
        retention: str = "10 days",
    ):
        """
        Initialize the asynchronous logger.

        :param log_file: The file to which logs are written.
                         If not provided, a file name based on the current time is used.
        :param log_level: The minimum log level (e.g. "DEBUG", "INFO").
        :param rotation: Log file rotation policy (e.g. "1 day" or "10 MB").
        :param retention: Log file retention policy (e.g. "10 days").
        """
        self.log_level = log_level.upper()
        # Remove any pre-existing sinks.
        loguru_logger.remove()

        # --- Console Sink ---
        # Use sys.stdout; the sink runs with enqueue=True to offload I/O.
        loguru_logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{file}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>",
            level=self.log_level,
            enqueue=True,
        )

        # --- File Sink ---
        if log_file is None:
            # Create a unique file name based on the current epoch (in milliseconds)
            current_epoch = int(datetime.now().timestamp() * 1000)
            log_file = f"resume-parser_{current_epoch}.log"
        loguru_logger.add(
            log_file,
            rotation=rotation,
            retention=retention,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{file}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>",
            level=self.log_level,
            enqueue=True,
        )

    async def _log(self, level: str, *args: Any, **kwargs: Any) -> None:
        """
        Internal helper: format the message and log at the given level.
        The actual call is synchronous but offloaded via Loguru’s enqueue.
        We add a trivial await (asyncio.sleep(0)) so that this method can be awaited.
        """
        # Concatenate all positional arguments into a single message string.
        message = " ".join(map(str, args))
        # Use Loguru’s .opt() to capture the caller’s stack information.
        loguru_logger.opt(depth=2).log(level.upper(), message, **kwargs)
        # Yield control to the event loop.
        await asyncio.sleep(0)

    async def debug(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously log a DEBUG-level message."""
        await self._log("DEBUG", *args, **kwargs)

    async def info(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously log an INFO-level message."""
        await self._log("INFO", *args, **kwargs)

    async def warning(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously log a WARNING-level message."""
        await self._log("WARNING", *args, **kwargs)

    async def error(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously log an ERROR-level message."""
        await self._log("ERROR", *args, **kwargs)

    async def critical(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously log a CRITICAL-level message."""
        await self._log("CRITICAL", *args, **kwargs)

    def log_message(self, *args: Any, level: str = "INFO", **kwargs: Any) -> None:
        """
        Synchronously log a message at the specified log level.

        This method concatenates all positional arguments into a single string,
        captures the caller’s stack information (by using an appropriate depth), and
        logs the message immediately.

        :param args: Positional arguments that form the log message.
        :param level: The log level at which to log (e.g., "DEBUG", "INFO", etc.).
                      Defaults to "INFO".
        :param kwargs: Additional keyword arguments passed to the underlying logger.
        """
        message = " ".join(map(str, args))
        # Use opt(depth=2) so that the caller’s frame is captured in the log record.
        loguru_logger.opt(depth=2).log(level.upper(), message, **kwargs)

    def bind(self, **kwargs: Any) -> "AppLogger":
        """
        Bind additional context (e.g. module or request id) to the logger.
        Returns a new AsyncLogger instance that uses the bound Loguru logger.
        """
        bound_instance = AppLogger.__new__(AppLogger)
        # Copy configuration from the current logger.
        bound_instance.log_level = self.log_level
        # Bind context to the underlying Loguru logger.
        bound_instance._bound_logger = loguru_logger.bind(**kwargs)
        # In our async helper, we delegate to the global loguru_logger.
        # (The bound logger will be used automatically.)
        return bound_instance


app_logger = AppLogger()


if __name__ == "__main__":
    import asyncio

    async def demo_logging():
        # Create an instance of the async logger.
        async_logger = AppLogger(log_level="DEBUG")

        # Simple log messages at various levels.
        await async_logger.info("This is an asynchronous info message.")
        await async_logger.debug("Debug details:", {"key": "value"})
        await async_logger.warning("This is a warning!")
        await async_logger.error("An error occurred:", Exception("Example error"))
        await async_logger.critical("Critical issue encountered!")

        # Example of binding extra context:
        logger_with_ctx = async_logger.bind(module="demo_module")
        await logger_with_ctx.info("This log message includes extra context.")


    # Run the async logging demo.
    asyncio.run(demo_logging())
