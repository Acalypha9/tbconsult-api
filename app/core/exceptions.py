class TriageServiceError(Exception):
    pass

class LLMUnavailableError(TriageServiceError):
    pass

class RetrievalError(TriageServiceError):
    pass

class RateLimitExceededError(TriageServiceError):
    pass

class RedFlagDetectedError(TriageServiceError):
    def __init__(self, message: str, escalation_response: str):
        super().__init__(message)
        self.escalation_response = escalation_response