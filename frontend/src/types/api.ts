export interface ApiSuccessResponse<T> {
  success: true;
  data: T;
  metadata: Record<string, unknown>;
  request_id: string;
}

export interface ApiErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
  };
  request_id: string;
}

export interface HealthStatus {
  status: string;
  environment: string;
  request_id: string;
}
