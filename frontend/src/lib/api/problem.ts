/**
 * RFC 9457 Problem Details returned by the SerpTank API. Clients branch on `code`
 * (stable), never on human-readable text.
 */
export interface Problem {
  type: string;
  title: string;
  status: number;
  code: string;
  detail?: string;
  trace_id?: string | null;
  errors?: { field: string; message: string; type: string }[];
  [key: string]: unknown;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly problem: Problem;

  constructor(problem: Problem) {
    super(problem.detail ?? problem.title);
    this.name = "ApiError";
    this.status = problem.status;
    this.code = problem.code;
    this.problem = problem;
  }

  /** Message safe to show to users. */
  get userMessage(): string {
    return this.problem.detail ?? this.problem.title;
  }

  fieldErrors(): Record<string, string> {
    return Object.fromEntries((this.problem.errors ?? []).map((e) => [e.field, e.message]));
  }
}

export function isProblem(value: unknown): value is Problem {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as Problem).code === "string" &&
    typeof (value as Problem).status === "number"
  );
}

export function toApiError(status: number, body: unknown): ApiError {
  if (isProblem(body)) return new ApiError(body);
  return new ApiError({
    type: "about:blank",
    title: status >= 500 ? "Something went wrong" : "Request failed",
    status,
    code: status >= 500 ? "internal_error" : "http_error",
  });
}
