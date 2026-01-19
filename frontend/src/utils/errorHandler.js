/**
 * Error handling utilities
 * Provides centralized error handling and user-friendly error messages
 */

/**
 * Extract error message from API error response
 */
export const getErrorMessage = (error) => {
  if (error.response) {
    // Server responded with error
    const { data } = error.response;

    if (typeof data === 'string') {
      return data;
    }

    if (data.detail) {
      if (typeof data.detail === 'string') {
        return data.detail;
      }
      if (Array.isArray(data.detail)) {
        return data.detail.map(err => err.msg || err.message).join(', ');
      }
    }

    if (data.message) {
      return data.message;
    }

    return 'Server error occurred';
  }

  if (error.request) {
    // Request made but no response
    return 'Network error. Please check your connection.';
  }

  // Error in request setup or other error
  return error.message || 'An unexpected error occurred';
};

/**
 * Check if error is a network error
 */
export const isNetworkError = (error) => {
  return !error.response && error.request;
};

/**
 * Check if error is unauthorized
 */
export const isUnauthorizedError = (error) => {
  return error.response && error.response.status === 401;
};

/**
 * Check if error is a validation error
 */
export const isValidationError = (error) => {
  return error.response && error.response.status === 422;
};

/**
 * Handle API error with user notification
 */
export const handleApiError = (error, customMessage = null) => {
  const message = customMessage || getErrorMessage(error);

  // Log to console for debugging
  console.error('API Error:', error);

  // You can integrate with a toast notification system here
  // For now, we'll return the message for the component to handle
  return message;
};

/**
 * Retry helper for failed requests
 */
export const retryRequest = async (requestFn, maxRetries = 3, delay = 1000) => {
  let lastError;

  for (let i = 0; i < maxRetries; i++) {
    try {
      return await requestFn();
    } catch (error) {
      lastError = error;

      // Don't retry on validation errors or unauthorized
      if (isValidationError(error) || isUnauthorizedError(error)) {
        throw error;
      }

      // Wait before retrying (exponential backoff)
      if (i < maxRetries - 1) {
        await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)));
      }
    }
  }

  throw lastError;
};

/**
 * Format validation errors for display
 */
export const formatValidationErrors = (error) => {
  if (!isValidationError(error)) {
    return {};
  }

  const errors = {};
  const details = error.response.data.detail;

  if (Array.isArray(details)) {
    details.forEach(err => {
      const field = err.loc ? err.loc[err.loc.length - 1] : 'general';
      errors[field] = err.msg || err.message;
    });
  }

  return errors;
};
