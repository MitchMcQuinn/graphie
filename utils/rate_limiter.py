import time
import threading
import logging
from collections import deque, defaultdict

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RateLimiter:
    """
    A token bucket rate limiter for API calls
    
    This class implements a token bucket algorithm to enforce rate limits
    on API calls, ensuring we don't exceed API provider limits.
    """
    
    def __init__(self, tokens_per_second=1, bucket_size=10):
        """
        Initialize the rate limiter
        
        Args:
            tokens_per_second: The number of tokens to add per second
            bucket_size: The maximum number of tokens the bucket can hold
        """
        self.tokens_per_second = tokens_per_second
        self.bucket_size = bucket_size
        self.tokens = bucket_size  # Start with a full bucket
        self.last_refill = time.time()
        self.lock = threading.RLock()  # Use a reentrant lock for safety
        
        # Track in-flight requests per model
        self.in_flight = defaultdict(int)
        self.in_flight_lock = threading.RLock()
        
        # Queue for pending requests
        self.pending_requests = deque()
        self.pending_lock = threading.RLock()
        
        # Start a background thread to process pending requests
        self._start_background_processor()
    
    def _start_background_processor(self):
        """Start a background thread to process pending requests"""
        thread = threading.Thread(target=self._process_pending_requests, daemon=True)
        thread.start()
    
    def _process_pending_requests(self):
        """Process pending requests in the background"""
        while True:
            try:
                # Sleep a bit to avoid tight looping
                time.sleep(0.1)
                
                # Check if there are any pending requests
                with self.pending_lock:
                    if not self.pending_requests:
                        continue
                
                # Try to acquire a token and process the next request
                if self.try_acquire():
                    with self.pending_lock:
                        if self.pending_requests:
                            request_info = self.pending_requests.popleft()
                            callback, model = request_info
                            
                            # Mark this model as having an in-flight request
                            with self.in_flight_lock:
                                self.in_flight[model] += 1
                            
                            # Execute the callback in a separate thread to avoid blocking
                            threading.Thread(target=self._execute_callback, 
                                             args=(callback, model), 
                                             daemon=True).start()
            except Exception as e:
                logger.error(f"Error in request processor: {str(e)}")
    
    def _execute_callback(self, callback, model):
        """Execute a callback and mark it as complete when done"""
        try:
            callback()
        except Exception as e:
            logger.error(f"Error executing callback: {str(e)}")
        finally:
            # Mark this model as no longer having an in-flight request
            with self.in_flight_lock:
                self.in_flight[model] -= 1
                if self.in_flight[model] <= 0:
                    del self.in_flight[model]
    
    def _refill_tokens(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Calculate new tokens to add
        new_tokens = elapsed * self.tokens_per_second
        
        # Update token count, but don't exceed bucket size
        self.tokens = min(self.tokens + new_tokens, self.bucket_size)
        
        # Update last refill time
        self.last_refill = now
    
    def try_acquire(self):
        """
        Try to acquire a token, returning immediately
        
        Returns:
            True if a token was acquired, False otherwise
        """
        with self.lock:
            self._refill_tokens()
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False
    
    def acquire(self, blocking=True, timeout=None):
        """
        Acquire a token, blocking if necessary
        
        Args:
            blocking: Whether to block until a token is available
            timeout: Maximum time to block (seconds), or None for no timeout
            
        Returns:
            True if a token was acquired, False otherwise
        """
        if not blocking:
            return self.try_acquire()
        
        # Calculate the end time for timeout
        end_time = None
        if timeout is not None:
            end_time = time.time() + timeout
        
        # Keep trying until we get a token or time out
        while True:
            if self.try_acquire():
                return True
            
            # Check if we've timed out
            if end_time is not None and time.time() >= end_time:
                return False
            
            # Sleep briefly to avoid tight looping
            time.sleep(0.1)
    
    def queue_request(self, callback, model="default"):
        """
        Queue a request to be executed when a token is available
        
        Args:
            callback: The function to call when a token is available
            model: The model identifier to track in-flight requests
            
        Returns:
            True if the request was queued, False if the model already has an in-flight request
        """
        # Check if this model already has an in-flight request
        with self.in_flight_lock:
            if model in self.in_flight and self.in_flight[model] > 0:
                logger.info(f"Model {model} already has an in-flight request, not queuing")
                return False
        
        # Queue the request
        with self.pending_lock:
            self.pending_requests.append((callback, model))
            logger.info(f"Queued request for model {model}, position {len(self.pending_requests)}")
        
        return True
    
    def get_queue_length(self):
        """Get the current length of the pending request queue"""
        with self.pending_lock:
            return len(self.pending_requests)
    
    def get_in_flight_count(self, model=None):
        """
        Get the number of in-flight requests
        
        Args:
            model: Optional model to get count for, or None for all models
            
        Returns:
            The number of in-flight requests
        """
        with self.in_flight_lock:
            if model is not None:
                return self.in_flight.get(model, 0)
            return sum(self.in_flight.values())

# Create a singleton instance for OpenAI API calls
# Default to 3 requests per second with a burst capacity of 10
openai_limiter = RateLimiter(tokens_per_second=3, bucket_size=10)

def get_openai_limiter():
    """Get the singleton OpenAI rate limiter instance"""
    return openai_limiter 